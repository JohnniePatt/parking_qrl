"""Phase 2 interface; intentionally contains no substitute random policy."""


class Model:
    def __init__(self, config):
        self.config = config

    def act(self, observation):
        raise NotImplementedError('Classical RL model is planned for phase 2')
