from typing import Optional

from pydantic import BaseModel


class Event(BaseModel):
    title: str
    link: Optional[str]
    description: str
    when: str
    location: str
    price: str
    target_age: list[str]


class EventsResult(BaseModel):
    events: list[Event]
    other_urls: list[str]
