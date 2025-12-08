from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.parse import urlparse

import structlog
from google import genai

import simplify_url
from agent_util import build_prompt
from agents.gemini_event_research_agent import (
    Event,
    EventsResult,
    GeminiEventResearchAgent,
)

logger = structlog.get_logger()


class EventListAgent(GeminiEventResearchAgent):
    def __init__(
        self, start_url: str, use_selenium: bool = False, start_url_params=None
    ):
        self.start_url = start_url
        self.start_url_params: dict | None = start_url_params
        parsed_url = urlparse(self.start_url)
        self.url_base = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.use_selenium = use_selenium
        super().__init__()

    def run(
        self,
        llm: genai.Client,
        events_start: date,
        events_finish: date,
        event_pages_limit: int | None = None,
    ) -> EventsResult:
        url = self.start_url

        if self.start_url_params:
            url += "?" + "&".join(
                [
                    name
                    + "="
                    + str(
                        eval(
                            value,
                            {
                                "events_start": events_start,
                                "events_finish": events_finish,
                            },
                        )
                    )
                    for name, value in self.start_url_params.items()
                ]
            )

        start_page = simplify_url.get(url, use_selenium=self.use_selenium)

        prompt = build_prompt(
            "prompts/event_list_start.txt",
            start_page=start_page,
            year=events_start.year,
            start_date=events_start.isoformat(),
            finish_date=events_finish.isoformat(),
        )
        response = self.ask_gemini(llm, "gemini-2.5-flash-lite", prompt, EventsResult)

        if response is None:
            return EventsResult(events=[])

        result: EventsResult = response.parsed

        for event in result.events:
            if event.link and event.link[0] == "/":
                event.link = self.url_base + event.link

        with ThreadPoolExecutor(max_workers=8) as executor:

            def threaded_update_from_link(params):
                return self.update_from_link(params[0], params[1])

            updated_events = executor.map(
                threaded_update_from_link, [(llm, event) for event in result.events]
            )

        result.events = list(updated_events)
        return result

    def update_from_link(self, llm: genai.Client, event: Event) -> Event:
        if event.link is None:
            return event

        page = simplify_url.get(event.link, self.use_selenium)
        prompt = build_prompt(
            "prompts/event_list_update.txt",
            event=event.model_dump_json(),
            page=page,
        )
        response = self.ask_gemini(llm, "gemini-2.5-flash-lite", prompt, Event)
        new_event: Event = response.parsed
        return new_event
