"""Background training jobs; independent environments keep manual editing untouched."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from threading import Event,Lock,Thread
from time import perf_counter
from uuid import uuid4
import hashlib
import json
import math


def write_json(path,value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    temporary.replace(path)


def validate_config(config):
    for key,maximum in [('episodes',10000),('max_actions',1000),('evaluation_interval',10000)]:
        if type(config[key]) is not int or not 1<=config[key]<=maximum:raise ValueError('Invalid '+key)
    if config.get('algorithm')!='DQN' or config.get('model')!='Model_RL':raise ValueError('Expected Model_RL DQN configuration')
    if type(config['seed']) is not int or not 0<=config['seed']<2**31:raise ValueError('Invalid seed')
    for key in ('training_seeds','test_seeds'):
        if not config[key] or len(config[key])>100 or any(type(s) is not int for s in config[key]):raise ValueError('Invalid '+key)
    if set(config['training_seeds']) & set(config['test_seeds']):raise ValueError('Train/test seeds must be disjoint')
    hp=config['hyperparameters']
    if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in hp.values()):raise ValueError('Invalid hyperparameters')
    for key in ('batch_size','replay_capacity','learning_starts','target_update_interval','epsilon_decay_steps'):
        if type(hp[key]) is not int or hp[key]<1:raise ValueError('Invalid '+key)
    if hp['batch_size']>hp['replay_capacity'] or hp['learning_starts']>hp['replay_capacity']:raise ValueError('Replay capacity too small')
    if not 0<=hp['epsilon_end']<=hp['epsilon_start']<=1 or not 0<=hp['gamma']<=1:raise ValueError('Invalid epsilon/gamma')
    if not 0<hp['learning_rate']<=1 or hp['gradient_clip']<=0:raise ValueError('Invalid learning rate/gradient clip')


class Jobs:
    def __init__(self,root,make_environment):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.make_environment=make_environment;self.lock=Lock();self.stop_event=Event();self.thread=None
        self.progress=dict(status='idle',episodes_completed=0,metrics=[],evaluations=[])
        self._restore_latest()

    def _restore_latest(self):
        manifests=sorted(self.root.glob('*/manifest.json'),reverse=True)
        if not manifests:return
        try:self.progress=self.results(manifests[0].parent.name)
        except (OSError,ValueError,KeyError):return

    def results(self,run_id):
        if run_id not in {p.parent.name for p in self.root.glob('*/manifest.json')}:
            raise ValueError('Unknown training run')
        directory=self.root/run_id
        record=json.loads((directory/'manifest.json').read_text())
        data=json.loads((directory/'metrics.json').read_text()) if (directory/'metrics.json').exists() else {'training':[],'test':[]}
        mode=record['mode'];rows=data['training'] if mode=='train' else data['test']
        files=sorted(directory.glob(mode+'_*.json'))
        return dict(status='interrupted' if record['status']=='running' else record['status'],
            mode=mode,id=directory.name,episodes_completed=sum(r['end_reason']!='cancelled' for r in rows),
            episodes_total=record['config']['episodes'] if mode=='train' else len(record['config']['test_seeds']),
            metrics=rows,evaluations=data['test'] if mode=='train' else [],config=record['config'],
            max_actions=record['config']['max_actions'],steps=record['steps'],updates=record['updates'],
            phase=mode,action=rows[-1]['actions'] if rows else 0,epsilon=rows[-1]['epsilon'] if rows else 0,
            elapsed_seconds=record.get('elapsed_seconds',0),error=record.get('error'),
            latest_output='Model_RL/'+directory.name+'/'+files[-1].name if files else None)

    def status(self):
        with self.lock:return deepcopy(self.progress)

    def update(self,**values):
        with self.lock:self.progress.update(deepcopy(values))

    def runs(self):
        runs=[]
        for manifest in sorted(self.root.glob('*/manifest.json'),reverse=True):
            try:
                record=json.loads(manifest.read_text())
                if (manifest.parent/'checkpoint.pt').exists():runs.append(dict(id=manifest.parent.name,**record))
            except (OSError,ValueError):continue
        return runs

    def start(self,config,mode='train',run_id=None):
        validate_config(config)
        if mode not in ('train','test'):raise ValueError('Mode must be train or test')
        with self.lock:
            if self.thread and self.thread.is_alive():raise ValueError('A model job is already running')
            checkpoint=None
            if mode=='test':
                if run_id not in [r['id'] for r in self.runs()]:raise ValueError('Choose an existing trained run')
                checkpoint=self.root/run_id/'checkpoint.pt'
                source=json.loads((checkpoint.parent/'manifest.json').read_text())
                # Test must use the saved training configuration, not silently change its task.
                config=source['config']
            job_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid4().hex[:8]
            directory=self.root/job_id;directory.mkdir()
            self.stop_event.clear()
            self.progress=dict(status='running',mode=mode,phase=mode,id=job_id,source_run=run_id,
                episodes_completed=0,episode=0,action=0,max_actions=config['max_actions'],
                episodes_total=config['episodes'] if mode=='train' else len(config['test_seeds']),
                steps=0,updates=0,epsilon=0 if mode=='test' else config['hyperparameters']['epsilon_start'],
                metrics=[],evaluations=[],elapsed_seconds=0,config=deepcopy(config),latest_output=None,error=None)
            self.thread=Thread(target=self._run,args=(deepcopy(config),mode,directory,checkpoint),daemon=True)
            self.thread.start()
        return self.status()

    def stop(self):
        self.stop_event.set()
        if self.status()['status']=='running':self.update(status='stopping')
        return self.status()

    def _run(self,config,mode,directory,checkpoint):
        start=perf_counter();metrics=[];evaluations=[];model=None;signature=None
        try:
            from Models.Model_RL.model import Model
            from Models.Model_RL.adapter import Adapter
            first=self.make_environment(config['training_seeds'][0],config)
            signature=dict(architecture='cnn16_32_pool4x6_mlp128_budget_dqn_v1',grid_shape=list(first.observation_space['grid'].shape),
                environment=deepcopy(first.config),policies=deepcopy(first.validator.policies),
                templates=deepcopy(first.templates),vehicle=deepcopy(first.validator.vehicle_auditor.profile),
                action_hash=hashlib.sha256(json.dumps(first.actions,sort_keys=True).encode()).hexdigest())
            model=Model(config,first.observation_space['grid'].shape,len(first.actions))
            if checkpoint:model.load(checkpoint,signature)
            total=config['episodes'] if mode=='train' else len(config['test_seeds'])
            best=-1
            # Reuse each seed's validator cache; environments reset for every episode.
            environments={config['training_seeds'][0]:first}
            def environment(seed):
                if seed not in environments:environments[seed]=self.make_environment(seed,config)
                return environments[seed]
            def episode(seed,index,training,folder):
                episode_start=perf_counter()
                model.online.train(training)
                self.update(episode=index,action=0,phase='train' if training else 'test')
                env=environment(seed);obs,_=env.reset(seed=config['seed']+index)
                adapter=Adapter(model,env);losses=[];reason='cancelled'
                while not self.stop_event.is_set():
                    result=adapter.step(obs,training=training)
                    if result is None:reason='no_valid_actions';break
                    obs=result['observation']
                    if result['loss'] is not None:losses.append(result['loss'])
                    self.update(episode=index,action=len(env.controller.history),steps=model.steps,updates=model.updates,
                                epsilon=model.epsilon() if training else 0,elapsed_seconds=perf_counter()-start)
                    if result['done']:reason=result['end_reason'];break
                row=dict(episode=index,seed=seed,split='train' if training else 'test',
                    actions=len(env.controller.history),reward=env.episode_return,elapsed_seconds=perf_counter()-episode_start,
                    total_slots=env._info()['total_slots'],verified_slots=env.assessment['passed'],
                    failed_slots=env.assessment['failed'],unknown_slots=env.assessment['unknown'],
                    utilization=env._info()['utilization'],loss=sum(losses)/len(losses) if losses else None,
                    epsilon=model.epsilon() if training else 0,end_reason=reason)
                snapshot=env.snapshot();snapshot.update(source='model_run',model='Model_RL',
                    training=training,run_id=directory.name,episode=index,split=row['split'],
                    model_config=config,training_metrics=row,
                    limitations=['Finite candidate catalogue','Bounded vehicle search; unknown is not infeasible','No engineering certification'])
                name=f'{folder}_{index:05d}_seed_{seed}.json'
                write_json(directory/name,snapshot)
                self.update(latest_output='Model_RL/'+directory.name+'/'+name)
                return row
            for index in range(1,total+1):
                if self.stop_event.is_set():break
                seed=(config['training_seeds'][(index-1)%len(config['training_seeds'])] if mode=='train' else config['test_seeds'][index-1])
                row=episode(seed,index,mode=='train',mode);metrics.append(row)
                if mode=='train':
                    model.save(directory/'checkpoint.pt',signature)
                    if row['verified_slots']>best:
                        best=row['verified_slots'];model.save(directory/'best.pt',signature)
                    if index%config['evaluation_interval']==0 and not self.stop_event.is_set():
                        for test_seed in config['test_seeds']:
                            if self.stop_event.is_set():break
                            test=episode(test_seed,index,False,'evaluation');evaluations.append(test)
                self.update(episodes_completed=index if row['end_reason']!='cancelled' else index-1,metrics=metrics,evaluations=evaluations)
                write_json(directory/'metrics.json',dict(training=metrics if mode=='train' else [],test=metrics if mode=='test' else evaluations))
                write_json(directory/'manifest.json',dict(model='Model_RL',algorithm='DQN',mode=mode,
                    status='running',config=config,environment_signature=signature,steps=model.steps,updates=model.updates,
                    source_run=checkpoint.parent.name if checkpoint else None))
            self.update(status='cancelled' if self.stop_event.is_set() else 'completed')
        except Exception as exc:
            self.update(status='failed',error=f'{type(exc).__name__}: {exc}')
        finally:
            self.update(elapsed_seconds=perf_counter()-start,metrics=metrics,evaluations=evaluations)
            write_json(directory/'manifest.json',dict(model='Model_RL',algorithm='DQN',mode=mode,status=self.status()['status'],
                config=config,environment_signature=signature,steps=model.steps if model else 0,
                updates=model.updates if model else 0,elapsed_seconds=perf_counter()-start,error=self.status().get('error')))
