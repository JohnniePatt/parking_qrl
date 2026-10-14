"""Called by main's future run orchestration, using the shared environment."""


class Adapter:
    def __init__(self, model, environment):
        self.model, self.environment = model, environment

    def step(self):
        return self.environment.step(self.model.act(self.environment.observation()))
