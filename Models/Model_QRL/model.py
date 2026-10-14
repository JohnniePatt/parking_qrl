"""Phase 2 interface; quantum circuits and backend are not implemented yet."""


class Model:
    def __init__(self, config):
        self.config = config

    def act(self, observation):
        raise NotImplementedError('Quantum RL model is planned for phase 2')
