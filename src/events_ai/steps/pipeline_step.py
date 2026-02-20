from abc import ABC, abstractmethod


class PipelineStep(ABC):
    @property
    @abstractmethod
    def done(self) -> bool:
        pass
