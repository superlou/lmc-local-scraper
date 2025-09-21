from datetime import datetime
from urllib.parse import urlparse

from devtools import debug
from google import genai
from pydantic import BaseModel

from agent_util import build_prompt
from event_list_agent import EventsResult
import simplify_url


class FlatEventPageAgent:
    def __init__(self, start_url: str, use_selenium: bool = False):
        self.start_url = start_url
        parsed_url = urlparse(self.start_url)
        self.url_base = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.use_selenium = use_selenium

    def run(self, llm: genai.Client) -> EventsResult:
        page = simplify_url.get(self.start_url, use_selenium=self.use_selenium)
        prompt = build_prompt(
            "agentic_approach/prompts/flat_events.txt",
            page=page,
            link=self.start_url,
            year=datetime.now().strftime("%Y"),
            today=datetime.now().strftime("%Y-%m-%d"),
        )

        response = llm.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=EventsResult,
            ),
        )
        result: EventsResult = response.parsed

        return result
