from typing import Optional
from dataclasses import dataclass


@dataclass
class Event:
    source: str
    title: str
    desc: str
    when: str
    location: Optional[str]
