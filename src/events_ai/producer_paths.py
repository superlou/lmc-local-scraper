from pathlib import Path
from typing import Generator


class ProducerPaths:
    def __init__(
        self,
        base: Path,
        events: str,
        script: str,
        storyboard: str,
        storyboard_pdf: str,
        video: str,
        post: str,
    ):
        self.base = base
        self.events = base / events
        self.script = base / script
        self.storyboard = base / storyboard
        self.storyboard_pdf = base / storyboard_pdf
        self.video = base / video
        self.post = base / post

    def events_for(self, org: str) -> Path:
        filename = f"{self.events.stem}_{org}{self.events.suffix}"
        return self.events.parent / filename

    def events_glob(self) -> Generator[Path, None, None]:
        return self.base.glob(self.events_for("*").name)
