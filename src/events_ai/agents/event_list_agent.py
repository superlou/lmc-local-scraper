from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.parse import urlparse

import structlog
from google import genai

from .. import simplify_url
from .gemini_event_research_agent import (
    Event,
    EventsResult,
    GeminiEventResearchAgent,
)
from .prompt import build_prompt

logger = structlog.get_logger()


class EventListAgent(GeminiEventResearchAgent):
    def __init__(
        self,
        llm: genai.Client,
        events_start: date,
        events_finish: date,
        start_url: str,
        use_selenium: bool = False,
        start_url_params=None,
    ):
        self.start_url = start_url
        self.start_url_params: str | None = start_url_params
        parsed_url = urlparse(self.start_url)
        self.url_base = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.use_selenium = use_selenium
        super().__init__(llm, events_start, events_finish)

    def run(self) -> EventsResult:
        url = self.start_url

        if self.start_url_params:
            param_vars = {
                "events_start": self.events_start,
                "events_finish": self.events_finish,
            }
            url += "?" + self.start_url_params.format(**param_vars)

        start_page = simplify_url.get(url, use_selenium=self.use_selenium)

        prompt = build_prompt(
            "event_list_start.txt.jinja2",
            start_page=start_page,
            start_date=self.events_start,
            finish_date=self.events_finish,
        )
        response = self.ask_gemini("gemini-2.5-flash-lite", prompt, EventsResult)

        if response is None:
            return EventsResult(events=[])

        result: EventsResult = response.parsed

        for event in result.events:
            if event.link and event.link[0] == "/":
                event.link = self.url_base + event.link

        with ThreadPoolExecutor(max_workers=8) as executor:

            def threaded_update_from_link(params):
                return self.update_from_link(params[0])

            updated_events = executor.map(
                threaded_update_from_link, [(event,) for event in result.events]
            )

        result.events = list(updated_events)
        return result

    def update_from_link(self, event: Event) -> Event:
        if event.link is None:
            return event

        page = simplify_url.get(event.link, self.use_selenium)
        prompt = build_prompt(
            "event_list_update.txt.jinja2",
            event=event.model_dump_json(),
            page=page,
            start_date=self.events_start,
            finish_date=self.events_finish,
        )
        response = self.ask_gemini("gemini-2.5-flash-lite", prompt, Event)
        new_event: Event = response.parsed
        return new_event
