from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urlparse

from devtools import debug
from google import genai
import structlog

from agent_util import build_prompt
from gemini_event_research_agent import GeminiEventResearchAgent, EventsResult, Event
import simplify_url

logger = structlog.get_logger()


class EventListAgent(GeminiEventResearchAgent):
    def __init__(self, start_url: str, use_selenium: bool = False):
        self.start_url = start_url
        parsed_url = urlparse(self.start_url)
        self.url_base = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.use_selenium = use_selenium
        super().__init__()

    def run(
        self, llm: genai.Client, event_pages_limit: int | None = None
    ) -> EventsResult:
        start_page = simplify_url.get(self.start_url, use_selenium=self.use_selenium)
        prompt = build_prompt(
            "agentic_approach/prompts/event_list_start.txt",
            start_page=start_page,
            year=datetime.now().strftime("%Y"),
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
            "agentic_approach/prompts/event_list_update.txt",
            event=event.model_dump_json(),
            page=page,
        )
        response = self.ask_gemini(llm, "gemini-2.5-flash-lite", prompt, Event)
        new_event: Event = response.parsed
        return new_event
