from datetime import date

from google import genai

from .gemini_event_research_agent import (
    EventsResult,
    GeminiEventResearchAgent,
)
from .prompt import build_prompt


class MarkdownEventsAgent(GeminiEventResearchAgent):
    def __init__(
        self,
        llm: genai.Client,
        events_start: date,
        events_finish: date,
        path: str,
        use_selenium: bool = False,
        start_url_params=None,
    ):
        self.path = path
        super().__init__(llm, events_start, events_finish)

    def run(self) -> EventsResult:
        page = open(self.path).read()

        prompt = build_prompt(
            "flat_events.txt.jinja2",
            page=page,
            start_date=self.events_start,
            finish_date=self.events_finish,
        )
        response = self.ask_gemini("gemini-2.5-flash-lite", prompt, EventsResult)

        if response is None:
            return EventsResult(events=[])

        result: EventsResult = response.parsed
        return result
