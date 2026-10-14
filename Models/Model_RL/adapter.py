"""The model interacts exclusively through the shared Environment API."""


class Adapter:
    def __init__(self, model, environment):
        self.model,self.environment=model,environment

    def step(self,observation,training=False):
        mask=self.environment.action_masks()
        if not mask.any():return None
        action=self.model.act(observation,mask,training=training)
        next_observation,reward,terminated,truncated,info=self.environment.step(action)
        next_mask=self.environment.action_masks()
        terminal=terminated or truncated
        loss=self.model.learn(observation,action,reward,next_observation,terminal,next_mask) if training else None
        return dict(observation=next_observation,reward=reward,done=terminal,info=info,loss=loss,action=action,
                    end_reason='finish' if self.environment.controller.history[-1]['command']['type']=='finish' else 'action_limit' if truncated else 'no_placement_actions' if terminated else None)
