class ServiceGenerationFailed(Exception):
    pass


class Service:
    def __init__(self):
        self.usages: list[ServiceUse] = []


class ServiceUse:
    @property
    def cost(self) -> float:
        raise NotImplementedError()
