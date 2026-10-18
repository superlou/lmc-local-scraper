import html
import urllib.parse
from datetime import date, datetime

import requests

from events_ai.agents.gemini_event_research_agent import (
    Event,
    EventsResult,
    TokenCounts,
)


class ReviseJSONAgent:
    def __init__(
        self,
        events_start: date,
        events_finish: date,
        json_url: str,
        organization: str,
    ):
        self.events_start = events_start
        self.events_finish = events_finish
        self.json_url = json_url
        self.organization = organization
        self.tokens = TokenCounts()

    def run(self) -> EventsResult:
        response = requests.get(self.json_url)
        data = response.json()

        return EventsResult(
            events=[
                Event(
                    organization=self.organization,
                    title=item["title"],
                    link=item.get("url", ""),
                    description=html.unescape(urllib.parse.unquote(item["desc"])),
                    when=item["start"],
                    location=item["location"],
                    price="",
                    target_age=[],
                )
                for item in data
                if (
                    (event_date := datetime.fromisoformat(item["start"]).date())
                    >= self.events_start
                )
                and event_date <= self.events_finish
            ]
        )
