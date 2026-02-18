from abc import ABC, abstractmethod


class PipelineStep(ABC):
    @abstractmethod
    def done(self) -> bool:
        pass
