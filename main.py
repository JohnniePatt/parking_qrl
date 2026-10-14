"""Composition root: connects UI, tools, policies, model scaffolds and storage."""
import argparse
from copy import deepcopy
from pathlib import Path
from time import perf_counter
from Arrange_tools.controller import Controller
from Arrange_tools.Policies.validator import Validator
from Arrange_tools.grid import dimensions, occupied_cells
from Layouts.generator import generate
from Layouts.repository import load, save
from Outputs.repository import Repository
from UI.server import serve

ROOT = Path(__file__).resolve().parent


class Application:
    def __init__(self):
        self.policies = load(ROOT/'Arrange_tools/policies.json')
        self.templates = load(ROOT/'Arrange_tools/Slot_layouts/slots.json')['templates']
        self.validator = Validator(self.policies, self.templates)
        self.outputs = Repository(ROOT/'Outputs')
        from Models.Model_RL.trainer import Jobs
        self.jobs=Jobs(ROOT/'Outputs/Model_RL',self.model_environment)
        self.controller = None
        self.new_session({'seed':42, 'resolution':0.25, 'max_actions':200})

    def model_environment(self,seed,model_config):
        from Models.environment import Environment
        config=load(ROOT/'Models/config.json')
        config.update(max_actions=model_config['max_actions'],seed=seed)
        validator=Validator(deepcopy(self.policies),deepcopy(self.templates))
        return Environment(generate(seed),deepcopy(self.templates),validator,config)

    def start_model(self,data):
        if data.get('model','Model_RL')!='Model_RL':
            raise ValueError('Model_QRL is not implemented yet')
        config=load(ROOT/'Models/Model_RL/config.json')
        for key in ('episodes','max_actions','seed'):
            if key in data:config[key]=data[key]
        from Models.datasets import validate_split
        validate_split(config)
        return self.jobs.start(config,data.get('mode','train'),data.get('run_id'))

    def new_session(self, data):
        seed = int(data.get('seed',42))
        resolution = float(data.get('resolution',0.25))
        limit = int(data.get('max_actions',200))
        if not 1 <= limit <= 10000:
            raise ValueError('Action limit must be 1–10000')
        layout = generate(seed)
        dimensions(layout,resolution)
        controller = Controller(layout,self.templates,self.validator,resolution,limit)
        for command in layout['starter_actions']:
            result = controller.apply(command)
            if not result['accepted']:
                raise ValueError('Starter layout is invalid: '+result['reason'])
        save(ROOT/'Layouts'/('rectangle_'+str(seed)+'.json'), layout)
        self.controller = controller
        self.environment = None
        self.vehicle_report = None
        return self.state()

    def reset_environment(self,data):
        from Models.environment import Environment
        config=load(ROOT/'Models/config.json')
        for key in ('resolution','max_actions','seed'):
            if key in data:
                config[key]=data[key]
        config['resolution']=float(config['resolution'])
        config['max_actions']=int(config['max_actions'])
        config['seed']=int(config['seed'])
        if not 1<=config['max_actions']<=10000:
            raise ValueError('Action limit must be 1-10000')
        layout=generate(config['seed'])
        environment=Environment(layout,self.templates,self.validator,config)
        environment.reset(seed=config['seed'])
        self.environment=environment
        self.controller=environment.controller
        self.vehicle_report=None
        return self.state()

    def restore_session(self,record):
        """Restore a backed-up manual session only if its final geometry is valid."""
        if record.get('schema_version')!=1 or record.get('source')!='manual_tools':
            raise ValueError('Only a version 1 manual session can be resumed')
        resolution=float(record['resolution'])
        dimensions(record['layout'],resolution)
        history=deepcopy(record['history'])
        items=deepcopy(record['final_items'])
        if len({i['id'] for i in items})!=len(items):
            raise ValueError('Duplicate object IDs in saved session')
        reason=self.validator.validate(items,record['layout'],resolution)
        legacy_traffic=(record.get('policies',{}).get('version',0)<4 and
                        reason and reason.startswith('slot_requires_entry_exit_connection:'))
        if reason and not legacy_traffic:
            raise ValueError('Saved layout does not satisfy current policy: '+reason)
        if history and history[-1]['after']!=items:
            raise ValueError('Saved history does not match final layout')
        controller=Controller(record['layout'],self.templates,self.validator,resolution,int(record['max_actions']))
        controller.items=items
        controller.history=history
        if history:
            controller.started=perf_counter()-float(history[-1].get('elapsed_seconds',0))
        self.migration_notice=('ผังเดิมใช้กฎไม่แยกทิศ: ตรวจลูกศรถนน 3.5 m และหมุนทิศให้เชื่อมเข้า–ออกได้' if legacy_traffic else None)
        self.controller=controller
        self.environment=None
        self.vehicle_report=None
        return self.state()

    def state(self):
        c = self.controller
        slots = [i for i in c.items if i['kind']=='slot']
        return dict(layout=c.layout, items=c.items, history=c.history, templates=self.templates,
                    migration_notice=getattr(self,'migration_notice',None),api_version=6,capabilities=['place_row','environment','policy_preview','vehicle_audit','directed_vehicle_paths','dqn_training'],
                    vehicle_report=self.environment.assessment if self.environment else self.vehicle_report,
                    grid=dimensions(c.layout,c.resolution), max_actions=c.max_actions,
                    metrics=dict(total_slots=len(slots), roads=sum(i['kind']=='road' for i in c.items),
                                 slot_area=round(sum(i['length']*i['width'] for i in slots),2),
                                 utilization=round(100*sum(i['length']*i['width'] for i in slots)/(c.layout['width']*c.layout['height']),2),
                                 rejected=sum(not e['accepted'] for e in c.history), actions=len(c.history)),
                    session_mode='environment_test' if self.environment else 'manual_tools',
                    environment_status=self.environment._info() if self.environment else None,
                    models={'Model_RL':'DQN','Model_QRL':'not_implemented'},
                    limitations=['Experimental vehicle and dimensions','Bounded path search; unknown is not infeasible','No engineering certification'])

    def action(self,data):
        if self.environment:
            raise ValueError('Use Environment step or start a new manual session')
        event = self.controller.apply(data)
        if event['accepted']:
            self.vehicle_report=None
            self.migration_notice=None
        return {'event':event,'state':self.state()}

    def save_output(self):
        if self.environment:
            return {'name':self.outputs.save(self.environment.snapshot())}
        c = self.controller
        return {'name':self.outputs.save(dict(schema_version=1, source='manual_tools', model=None,
                    layout=deepcopy(c.layout), resolution=c.resolution,max_actions=c.max_actions,
                    policies=deepcopy(self.policies),templates=deepcopy(self.templates),
                    history=deepcopy(c.history), initial_items=[], final_items=deepcopy(c.items),
                    vehicle_profile=deepcopy(self.validator.vehicle_auditor.profile),
                    vehicle_report=deepcopy(self.vehicle_report),
                    metrics=self.state()['metrics'], limitations=self.state()['limitations']))}

    def route(self, method, path, data):
        if method=='GET' and path=='/api/state':
            return self.state()
        if method=='GET' and path=='/api/outputs':
            return {'files':self.outputs.list()}
        if method=='GET' and path=='/api/layouts':
            return {'files':[p.name for p in sorted((ROOT/'Layouts').glob('*.json'))]}
        if method=='POST' and path=='/api/session':
            return self.new_session(data)
        if method=='POST' and path=='/api/action':
            return self.action(data)
        if method=='POST' and path=='/api/propose':
            return self.controller.propose(data)
        if method=='POST' and path=='/api/vehicle/check':
            self.vehicle_report=self.validator.audit(self.controller.items,self.controller.layout,self.controller.resolution)
            return {'report':self.vehicle_report,'state':self.state()}
        if method=='POST' and path=='/api/environment/reset':
            return self.reset_environment(data)
        if method=='GET' and path=='/api/environment/actions':
            if not self.environment:
                raise ValueError('Start an environment test first')
            mask=self.environment.action_masks()
            return {'actions':[dict(index=i,command=a,valid=bool(mask[i])) for i,a in enumerate(self.environment.actions)]}
        if method=='POST' and path=='/api/environment/step':
            if not self.environment:
                raise ValueError('Start an environment test first')
            _,reward,terminated,truncated,info=self.environment.step(data['action'])
            return dict(state=self.state(),reward=reward,terminated=terminated,truncated=truncated,info=info)
        if method=='POST' and path=='/api/save':
            return self.save_output()
        if method=='POST' and path=='/api/preview':
            return self.outputs.load(data['name'])
        if method=='GET' and path=='/api/grid':
            c = self.controller
            # Sparse channels keep road/slot/obstacle information separate.
            return {kind:sorted({cell for item in items for cell in occupied_cells(item,c.layout,c.resolution)})
                    for kind,items in [('obstacles',c.layout['obstacles']),
                                       ('roads',[i for i in c.items if i['kind']=='road']),
                                       ('slots',[i for i in c.items if i['kind']=='slot'])]}
        if method=='POST' and path=='/api/run':
            return self.start_model(data)
        if method=='GET' and path=='/api/training/status':
            return self.jobs.status()
        if method=='GET' and path=='/api/training/runs':
            return {'runs':self.jobs.runs(),'config':load(ROOT/'Models/Model_RL/config.json')}
        if method=='POST' and path=='/api/training/results':
            return self.jobs.results(data['run_id'])
        if method=='POST' and path=='/api/training/stop':
            return self.jobs.stop()
        raise ValueError('Unknown API route')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Parking layout research tools')
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--resume',type=Path,help='Resume a saved manual session after validating its final layout')
    args = parser.parse_args()
    application=Application()
    if args.resume:
        application.restore_session(load(args.resume))
    serve(application,ROOT/'UI',args.port)
