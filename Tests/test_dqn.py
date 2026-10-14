from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import numpy as np
import torch
from Models.Model_RL.model import Model
from Models.Model_RL.trainer import validate_config,Jobs
from main import Application

ROOT=Path(__file__).resolve().parents[1]


class DQNTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((ROOT/'Models/Model_RL/config.json').read_text())
        self.config['hyperparameters'].update(batch_size=1,learning_starts=1,replay_capacity=8,target_update_interval=2,gamma=.5)
        self.obs=dict(grid=np.zeros((5,8,8),dtype=np.uint8),budget=np.array([1],dtype=np.float32))
        self.model=Model(self.config,(5,8,8),3)
        with torch.no_grad():
            for net in (self.model.online,self.model.target):
                for param in net.parameters():param.zero_()
            self.model.target.head[-1].bias.copy_(torch.tensor([0.,100.,2.]))

    def test_bellman_target_masks_invalid_high_q_action(self):
        loss=self.model.learn(self.obs,0,1,self.obs,False,np.array([True,False,True]))
        self.assertAlmostEqual(loss,1.5,places=5)
        self.assertEqual(self.model.updates,1)
        self.assertNotEqual(float(self.model.online.head[-1].bias[0].detach()),0)

    def test_terminal_transition_never_bootstraps_and_target_syncs(self):
        for _ in range(2):self.model.learn(self.obs,0,1,self.obs,True,np.array([False]*3))
        self.assertEqual(self.model.updates,2)
        for actual,target in zip(self.model.online.parameters(),self.model.target.parameters()):
            self.assertTrue(torch.equal(actual,target))

    def test_test_mode_is_greedy_masked_and_does_not_learn(self):
        with torch.no_grad():self.model.online.head[-1].bias.copy_(torch.tensor([1.,100.,3.]))
        before=deepcopy(self.model.online.state_dict());rng=self.model.rng.getstate()
        for _ in range(3):self.assertEqual(self.model.act(self.obs,np.array([True,False,True]),False),2)
        self.assertEqual(self.model.steps,0);self.assertEqual(len(self.model.memory),0)
        self.assertEqual(self.model.rng.getstate(),rng)
        for key,value in before.items():self.assertTrue(torch.equal(value,self.model.online.state_dict()[key]))

    def test_checkpoint_round_trip_and_signature_guard(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'checkpoint.pt';signature={'action_hash':'abc'}
            self.model.save(path,signature)
            target=Model(self.config,(5,8,8),3);target.load(path,signature)
            for a,b in zip(self.model.online.parameters(),target.online.parameters()):self.assertTrue(torch.equal(a,b))
            with self.assertRaises(ValueError):target.load(path,{'action_hash':'wrong'})

    def test_invalid_configuration_and_shared_defaults(self):
        validate_config(self.config)
        bad=deepcopy(self.config);bad['test_seeds']=[42]
        with self.assertRaises(ValueError):validate_config(bad)
        bad=deepcopy(self.config);bad['episodes']=0
        with self.assertRaises(ValueError):validate_config(bad)
        from Models.datasets import validate_split
        validate_split(self.config)
        leak=deepcopy(self.config);leak['test_seeds']=[103]
        with self.assertRaises(ValueError):validate_split(leak)
        app=Application()
        env=app.model_environment(42,self.config)
        self.assertEqual(env.controller,None)
        self.assertEqual(env.config['max_actions'],50)
        self.assertIsNot(env.validator,app.validator)
        self.assertIn('dqn_training',app.state()['capabilities'])

    def test_background_failures_are_reported(self):
        def broken(seed,config):raise ValueError('fixture failure')
        with TemporaryDirectory() as directory:
            jobs=Jobs(directory,broken);jobs.start(self.config);jobs.thread.join(10)
            self.assertEqual(jobs.status()['status'],'failed')
            self.assertIn('fixture failure',jobs.status()['error'])

class SmallEnvironment:
    """Deterministic fast fixture for trainer lifecycle, independent of geometry tests."""
    def __init__(self,seed,config):
        from types import SimpleNamespace
        self.config={'resolution':.5,'max_actions':config['max_actions'],'seed':seed}
        self.actions=[{'type':'finish'},{'type':'place_row'}]
        self.observation_space=SimpleNamespace(spaces=None)
        self.observation_space={'grid':SimpleNamespace(shape=(5,8,8))}
        self.templates={}
        self.validator=SimpleNamespace(policies={},templates={},vehicle_auditor=SimpleNamespace(profile={}))
        self.controller=SimpleNamespace(history=[])
        self.assessment={'passed':0,'failed':0,'unknown':0};self.episode_return=0;self.done=False

    def observation(self):
        return dict(grid=np.full((5,8,8),len(self.controller.history)%2,dtype=np.uint8),
                    budget=np.array([1-len(self.controller.history)/4],dtype=np.float32))

    def reset(self,seed=None):
        self.controller.history=[];self.episode_return=0;self.done=False;self.assessment['passed']=0
        return self.observation(),self._info()

    def action_masks(self):return np.array([not self.done]*2)

    def step(self,action):
        self.controller.history.append({'command':self.actions[action]})
        self.done=action==0 or len(self.controller.history)>=3
        reward=float(action);self.episode_return+=reward;self.assessment['passed']+=action
        return self.observation(),reward,self.done,False,self._info()

    def _info(self):return dict(total_slots=self.assessment['passed'],utilization=self.assessment['passed']/10)

    def snapshot(self):return dict(schema_version=1,history=deepcopy(self.controller.history))


class JobTests(unittest.TestCase):
    def config(self):
        c=json.loads((ROOT/'Models/Model_RL/config.json').read_text())
        c.update(episodes=2,max_actions=4,evaluation_interval=1,training_seeds=[42],test_seeds=[101])
        c['hyperparameters'].update(batch_size=1,learning_starts=1,replay_capacity=8)
        return c

    def test_train_checkpoint_test_and_saved_snapshots(self):
        with TemporaryDirectory() as directory:
            jobs=Jobs(directory,SmallEnvironment);jobs.start(self.config());jobs.thread.join(30)
            state=jobs.status();self.assertEqual(state['status'],'completed',state)
            self.assertGreater(state['updates'],0);self.assertEqual(len(state['metrics']),2)
            self.assertEqual(len(state['evaluations']),2)
            run_id=state['id'];checkpoint=Path(directory)/run_id/'checkpoint.pt'
            before=checkpoint.read_bytes();updates=state['updates']
            self.assertTrue((Path(directory)/run_id/'metrics.json').exists())
            self.assertEqual(len(list((Path(directory)/run_id).glob('train_*.json'))),2)
            jobs.start(self.config(),'test',run_id);jobs.thread.join(30)
            state=jobs.status();self.assertEqual(state['status'],'completed',state)
            self.assertEqual(state['updates'],updates);self.assertEqual(state['epsilon'],0)
            self.assertEqual(checkpoint.read_bytes(),before)
            saved=jobs.results(run_id)
            self.assertEqual(len(saved['metrics']),2)
            self.assertEqual(saved['updates'],updates)
            with self.assertRaises(ValueError):jobs.results('../outside')
            self.assertTrue(all(r['loss'] is None and r['split']=='test' for r in state['metrics']))

    def test_cancellation_and_duplicate_job_guard(self):
        from threading import Event
        started,release=Event(),Event()
        def factory(seed,config):
            started.set();release.wait(10);return SmallEnvironment(seed,config)
        with TemporaryDirectory() as directory:
            jobs=Jobs(directory,factory);jobs.start(self.config());self.assertTrue(started.wait(10))
            with self.assertRaises(ValueError):jobs.start(self.config())
            self.assertEqual(jobs.stop()['status'],'stopping');release.set();jobs.thread.join(30)
            self.assertEqual(jobs.status()['status'],'cancelled')
