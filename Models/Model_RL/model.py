"""Masked DQN with a CNN grid encoder, replay and a separate target network."""
from collections import deque
from copy import deepcopy
import random
import numpy as np
import torch
from torch import nn


class Network(nn.Module):
    def __init__(self, channels, actions):
        super().__init__()
        self.encoder=nn.Sequential(nn.Conv2d(channels,16,3,stride=2,padding=1),nn.ReLU(),
            nn.Conv2d(16,32,3,stride=2,padding=1),nn.ReLU(),nn.AdaptiveAvgPool2d((4,6)),nn.Flatten())
        self.head=nn.Sequential(nn.Linear(32*4*6+1,128),nn.ReLU(),nn.Linear(128,actions))

    def forward(self, grid, budget):
        return self.head(torch.cat((self.encoder(grid),budget),dim=1))


def tensors(observations):
    return (torch.from_numpy(np.stack([o['grid'] for o in observations]).astype(np.float32)),
            torch.from_numpy(np.stack([o['budget'] for o in observations]).astype(np.float32)))


class Model:
    def __init__(self, config, observation_shape, action_count):
        self.config=deepcopy(config);self.hp=config['hyperparameters']
        torch.set_num_threads(1)
        torch.manual_seed(config['seed'])
        self.rng=random.Random(config['seed'])
        self.online=Network(observation_shape[0],action_count)
        self.target=deepcopy(self.online).eval()
        self.optimizer=torch.optim.Adam(self.online.parameters(),lr=self.hp['learning_rate'])
        self.memory=deque(maxlen=self.hp['replay_capacity'])
        self.steps=0;self.updates=0

    def epsilon(self):
        hp=self.hp
        fraction=min(1,self.steps/hp['epsilon_decay_steps'])
        return hp['epsilon_start']+fraction*(hp['epsilon_end']-hp['epsilon_start'])

    def act(self, observation, mask, training=False):
        valid=np.flatnonzero(mask)
        if not len(valid):raise ValueError('No valid actions')
        if training and self.rng.random()<self.epsilon():return int(self.rng.choice(valid))
        with torch.no_grad():
            q=self.online(*tensors([observation]))[0]
            q=q.masked_fill(~torch.as_tensor(mask,dtype=torch.bool),-torch.inf)
            return int(q.argmax())

    def learn(self, observation, action, reward, next_observation, terminal, next_mask):
        self.memory.append((observation,action,float(reward),next_observation,bool(terminal),next_mask.copy()))
        self.steps+=1
        if len(self.memory)<max(self.hp['batch_size'],self.hp['learning_starts']):return None
        samples=self.rng.sample(list(self.memory),self.hp['batch_size'])
        obs,actions,rewards,nxt,done,masks=zip(*samples)
        values=self.online(*tensors(obs)).gather(1,torch.tensor(actions).unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            qs=self.target(*tensors(nxt)).masked_fill(~torch.from_numpy(np.stack(masks)),-torch.inf)
            bootstrap=qs.max(1).values
            # Finite action horizon: terminal/truncated states do not bootstrap.
            bootstrap=torch.where(torch.tensor(done)|~torch.isfinite(bootstrap),0,bootstrap)
            expected=torch.tensor(rewards,dtype=torch.float32)+self.hp['gamma']*bootstrap
        loss=nn.functional.smooth_l1_loss(values,expected)
        self.optimizer.zero_grad();loss.backward()
        nn.utils.clip_grad_norm_(self.online.parameters(),self.hp['gradient_clip'])
        self.optimizer.step();self.updates+=1
        if self.updates%self.hp['target_update_interval']==0:self.target.load_state_dict(self.online.state_dict())
        return float(loss.detach())

    def save(self,path,signature):
        temporary=path.with_suffix('.tmp')
        torch.save(dict(schema_version=1,algorithm='DQN',config=self.config,signature=signature,
                        online=self.online.state_dict(),target=self.target.state_dict(),
                        optimizer=self.optimizer.state_dict(),steps=self.steps,updates=self.updates),temporary)
        temporary.replace(path)

    def load(self,path,signature):
        record=torch.load(path,map_location='cpu',weights_only=True)
        if record['signature']!=signature:raise ValueError('Checkpoint environment/action catalogue does not match')
        self.online.load_state_dict(record['online']);self.target.load_state_dict(record['target'])
        self.optimizer.load_state_dict(record['optimizer'])
        self.steps=record['steps'];self.updates=record['updates']
