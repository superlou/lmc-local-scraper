from datetime import datetime
from urllib.parse import urlparse

from google import genai
import structlog

from agent_util import build_prompt
from agents.gemini_event_research_agent import GeminiEventResearchAgent, EventsResult
import simplify_url


logger = structlog.get_logger()


class FlatEventPageAgent(GeminiEventResearchAgent):
    def __init__(self, start_url: str, use_selenium: bool = False):
        self.start_url = start_url
        parsed_url = urlparse(self.start_url)
        self.url_base = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.use_selenium = use_selenium
        super().__init__()

    def run(
        self, llm: genai.Client, events_start: datetime, events_finish: datetime
    ) -> EventsResult:
        page = simplify_url.get(self.start_url, use_selenium=self.use_selenium)
        prompt = build_prompt(
            "prompts/flat_events.txt",
            page=page,
            link=self.start_url,
            year=datetime.now().strftime("%Y"),
            today=datetime.now().strftime("%Y-%m-%d"),
        )
        response = self.ask_gemini(llm, "gemini-2.5-flash-lite", prompt, EventsResult)

        if response is None:
            logger.warn(f"Failed to get events from {self.start_url}")

        result: EventsResult = response.parsed
        return result
