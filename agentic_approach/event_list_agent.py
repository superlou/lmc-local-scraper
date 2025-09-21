from urllib.parse import urlparse

from devtools import debug
from google import genai
from pydantic import BaseModel

from agent_util import build_prompt
import simplify_url


class Event(BaseModel):
    title: str
    link: str | None
    description: str
    when: str
    location: str
    price: str | None
    target_age: list[str]


class EventsResult(BaseModel):
    events: list[Event]


class EventListAgent:
    def __init__(self, start_url: str, use_selenium: bool = False):
        self.start_url = start_url
        parsed_url = urlparse(self.start_url)
        self.url_base = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.use_selenium = use_selenium

    def run(
        self,
        llm: genai.Client,
        event_pages_limit: int | None = None,
    ) -> EventsResult:
        start_page = simplify_url.get(self.start_url, use_selenium=self.use_selenium)
        print(start_page)
        prompt = build_prompt(
            "agentic_approach/prompts/event_list_start.txt", start_page=start_page
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

        for i, event in enumerate(result.events):
            if event_pages_limit is not None and i >= event_pages_limit:
                break

            if event.link is None:
                continue

            print(f"[{i + 1}/{len(result.events)}] Following {event.link}")

            if event.link[0] == "/":
                event.link = self.url_base + event.link

            event_page = simplify_url.get(event.link, self.use_selenium)
            result = self.update_with_details(llm, event_page, result)
            debug(result)

        return result

    def update_with_details(
        self, llm: genai.Client, page: str, result: EventsResult,
    ) -> EventsResult:
        prompt = build_prompt(
            "agentic_approach/prompts/event_list_update.txt",
            previous_results=result.model_dump_json(),
            page=page,
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

        new_result: EventsResult = response.parsed
        return new_result
