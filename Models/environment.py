"""Gymnasium environment; geometry and feasibility remain in Arrange_tools."""
from copy import deepcopy
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from Arrange_tools.controller import Controller
from Arrange_tools.grid import dimensions, occupied_cells
from Models.actions import catalogue, decode
from Models.rewards import calculate


class Environment(gym.Env):
    metadata={'render_modes':[]}

    def __init__(self,layout,templates,validator,config):
        super().__init__()
        self.layout=deepcopy(layout)
        self.templates,self.validator=templates,validator
        self.config=deepcopy(config)
        if int(config['max_actions'])<1:
            raise ValueError('max_actions must be positive')
        size=dimensions(layout,config['resolution'])
        self.actions=catalogue(layout,config)
        self.action_space=spaces.Discrete(len(self.actions))
        self.observation_space=spaces.Dict({
            'grid':spaces.Box(0,1,shape=(5,size['rows'],size['columns']),dtype=np.uint8),
            'budget':spaces.Box(0,1,shape=(1,),dtype=np.float32)})
        self.controller=None
        self._done=False
        self._mask_cache=None
        self._static_grid=None

    def reset(self,*,seed=None,options=None):
        super().reset(seed=seed)
        options=options or {}
        self.controller=Controller(self.layout,self.templates,self.validator,
                                   self.config['resolution'],int(self.config['max_actions']))
        if options.get('start_with_road',self.config.get('start_with_road',False)):
            self.controller.initialize(self.layout.get('starter_actions',[]))
        self.initial_items=deepcopy(self.controller.items)
        self._done=False
        self._mask_cache=None
        self._static_grid=None
        self.episode_return=0.0
        self.assessment=self.validator.audit(self.controller.items,self.layout,self.config['resolution'])
        return self.observation(),self._info()

    def _require_reset(self):
        if self.controller is None:
            raise RuntimeError('Call reset() before using the environment')

    def step(self,action):
        self._require_reset()
        if self._done:
            raise RuntimeError('Episode ended; call reset()')
        if not self.action_space.contains(action):
            raise ValueError('Action index is outside the catalogue')
        command=decode(self.actions,int(action))
        before_passed=self.assessment['passed']
        event=self.controller.apply(command)
        if event['accepted'] and command['type']!='finish':
            self.assessment=self.validator.audit(self.controller.items,self.layout,self.config['resolution'])
        event['vehicle_counts']={'before_passed':before_passed,'after_passed':self.assessment['passed']}
        event['vehicle_assessment']={k:self.assessment[k] for k in ('passed','failed','unknown')}
        reward,terms=calculate(event,self.config['reward'])
        self.episode_return+=reward
        terminated=command['type']=='finish'
        truncated=not terminated and len(self.controller.history)>=self.controller.max_actions
        self._done=terminated or truncated
        self._mask_cache=None
        if not self._done and not self.action_masks()[1:].any():
            terminated=True
            self._done=True
        event.update(reward=reward,reward_terms=terms,terminated=terminated,truncated=truncated)
        return self.observation(),reward,terminated,truncated,self._info(event)

    def observation(self):
        self._require_reset()
        c=self.controller
        shape=self.observation_space['grid'].shape
        if self._static_grid is None:
            self._static_grid=np.zeros(shape,dtype=np.uint8)
            for obstacle in c.layout['obstacles']:
                for col,row in occupied_cells(obstacle,c.layout,c.resolution):
                    self._static_grid[0,row,col]=1
            for gate in c.layout['gates']:
                channel=3 if gate['role']=='entry' else 4
                for col,row in occupied_cells(gate['reserve'],c.layout,c.resolution):
                    self._static_grid[channel,row,col]=1
        grid=self._static_grid.copy()
        for item in c.items:
            channel=1 if item['kind']=='road' else 2
            for col,row in occupied_cells(item,c.layout,c.resolution):
                grid[channel,row,col]=1
        remaining=max(0,1-len(c.history)/c.max_actions)
        return {'grid':grid,'budget':np.array([remaining],dtype=np.float32)}

    def action_masks(self):
        """Current-policy mask. Mask generation never logs an action."""
        self._require_reset()
        if self._done:
            return np.zeros(len(self.actions),dtype=bool)
        if self._mask_cache is None:
            self._mask_cache=np.array([self.controller.propose(a)['accepted'] for a in self.actions],dtype=bool)
        return self._mask_cache.copy()

    def _info(self,event=None):
        c=self.controller
        slots=sum(i['kind']=='slot' for i in c.items)
        deterministic_event=deepcopy(event)
        if deterministic_event:
            deterministic_event.pop('timestamp',None)
            deterministic_event.pop('elapsed_seconds',None)
        return dict(total_slots=slots,slot_area=slots*13.75,
                    utilization=slots*13.75/(c.layout['width']*c.layout['height']),
                    actions=len(c.history),episode_return=self.episode_return,
                    last_reward=c.history[-1].get('reward',0.0) if c.history else 0.0,
                    episode_finished=self._done,
                    vehicle_passed=self.assessment['passed'],vehicle_failed=self.assessment['failed'],vehicle_unknown=self.assessment['unknown'],
                    event=deterministic_event,feasibility='bounded_bicycle_path_witnesses',swept_path_checked=True,certification=False)

    def snapshot(self):
        self._require_reset()
        return dict(schema_version=1,source='environment_test',model=None,
                    layout=deepcopy(self.layout),resolution=self.controller.resolution,
                    max_actions=self.controller.max_actions,policies=deepcopy(self.validator.policies),
                    templates=deepcopy(self.templates),config=deepcopy(self.config),
                    initial_items=deepcopy(self.initial_items),history=deepcopy(self.controller.history),
                    final_items=deepcopy(self.controller.items),metrics=self._info(),
                    action_catalogue=deepcopy(self.actions),
                    vehicle_report=deepcopy(self.assessment),
                    limitations=['No trained model','Bounded path templates; unknown is not infeasible','No engineering certification'])
