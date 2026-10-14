"""Future models receive the same injected controller; no duplicate policies."""


class Environment:
    def __init__(self, controller):
        self.controller = controller

    def step(self, action):
        event = self.controller.apply(action)
        return {'event':event, 'terminated':len(self.controller.history)>=self.controller.max_actions}

    def observation(self):
        from copy import deepcopy
        return deepcopy({'layout':self.controller.layout,'items':self.controller.items,
                         'resolution':self.controller.resolution})

    # Reward design, reset protocol and model observation encoding belong to phase 2.
