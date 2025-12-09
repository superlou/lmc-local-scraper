from datetime import date
from urllib.parse import urlparse

import structlog
from google import genai

from .. import simplify_url
from .agent_util import build_prompt
from .gemini_event_research_agent import EventsResult, GeminiEventResearchAgent

logger = structlog.get_logger()


class FlatEventPageAgent(GeminiEventResearchAgent):
    def __init__(self, start_url: str, use_selenium: bool = False):
        self.start_url = start_url
        parsed_url = urlparse(self.start_url)
        self.url_base = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.use_selenium = use_selenium
        super().__init__()

    def run(
        self, llm: genai.Client, events_start: date, events_finish: date
    ) -> EventsResult:
        page = simplify_url.get(self.start_url, use_selenium=self.use_selenium)
        prompt = build_prompt(
            "flat_events.txt",
            page=page,
            link=self.start_url,
            year=events_start.year,
            today=events_start.isoformat(),
            start_date=events_start.isoformat(),
            finish_date=events_finish.isoformat(),
        )
        response = self.ask_gemini(llm, "gemini-2.5-flash-lite", prompt, EventsResult)

        if response is None:
            logger.warn(f"Failed to get events from {self.start_url}")

        result: EventsResult = response.parsed
        return result
