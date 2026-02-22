from datetime import date
from urllib.parse import urlparse

import structlog
from google import genai
from pydantic import BaseModel

from .. import simplify_url
from .gemini_event_research_agent import Event, EventsResult, GeminiEventResearchAgent
from .prompt import build_prompt

logger = structlog.get_logger()


class RawEvent(BaseModel):
    info: str
    address: str


class SeparatedEvents(BaseModel):
    events: list[RawEvent]


class FlatEventPageAgent(GeminiEventResearchAgent):
    def __init__(
        self,
        llm: genai.Client,
        events_start: date,
        events_finish: date,
        start_url: str,
        use_selenium: bool = False,
        split_first: bool = False,
    ):
        self.start_url = start_url
        parsed_url = urlparse(self.start_url)
        self.url_base = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.use_selenium = use_selenium
        self.split_first = split_first
        super().__init__(llm, events_start, events_finish)

    def run(self) -> EventsResult:
        if self.split_first:
            return self.run_with_split_first()
        else:
            return self.run_in_one_step()

    def run_in_one_step(self) -> EventsResult:
        page = simplify_url.get(self.start_url, use_selenium=self.use_selenium)
        prompt = build_prompt(
            "flat_events.txt.jinja2",
            page=page,
            link=self.start_url,
            today=self.events_start,
            start_date=self.events_start,
            finish_date=self.events_finish,
        )
        response = self.ask_gemini("gemini-2.5-flash-lite", prompt, EventsResult)

        if response is None:
            logger.warn(f"Failed to get events from {self.start_url}")

        result: EventsResult = response.parsed
        return result

    def run_with_split_first(self) -> EventsResult:
        """
        Simple models appear more reliable if performed as two steps:
        1. Separate events information
        2. Extract event details
        """
        page = simplify_url.get(self.start_url, use_selenium=self.use_selenium)

        prompt = f"Split the following page into events. Including location information if it is found on the page. An event is expected to have a date, location, and description. Typically, each event starts with a title, then continues until the next event title.\n{page}"
        response = self.ask_gemini("gemini-2.5-flash-lite", prompt, SeparatedEvents)
        separated_events: SeparatedEvents = response.parsed
        print(separated_events)

        events = EventsResult(events=[])

        for raw_event in separated_events.events:
            prompt = build_prompt(
                "flat_page_event.txt.jinja2",
                event=raw_event,
                link=self.start_url,
                start_date=self.events_start,
                finish_date=self.events_finish,
            )
            logger.debug(f"Research prompt: {prompt}")
            response = self.ask_gemini("gemini-2.5-flash-lite", prompt, Event)
            events.events.append(response.parsed)

        return events
