from dataclasses import dataclass


from google import genai
from google.genai.types import GenerateContentResponse
from pydantic import BaseModel


class Event(BaseModel):
    organization: str
    title: str
    link: str | None
    description: str
    when: str
    location: str
    price: str | None
    target_age: list[str]


class EventsResult(BaseModel):
    events: list[Event]


@dataclass
class TokenCounts:
    prompt: int = 0
    candidates: int = 0
    total: int = 0


class GeminiEventResearchAgent:
    def __init__(self):
        self.tokens = TokenCounts()

    def ask_gemini(
        self, llm: genai.Client, model: str, prompt: str, response_schema
    ) -> GenerateContentResponse:
        response = llm.models.generate_content(
            model=model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )

        self.count_tokens(response)
        return response

    def count_tokens(self, response: GenerateContentResponse):
        if response is None or response.usage_metadata is None:
            return

        usage = response.usage_metadata

        self.tokens.prompt += usage.prompt_token_count or 0
        self.tokens.candidates += usage.candidates_token_count or 0
        self.tokens.total += response.usage_metadata.total_token_count or 0
