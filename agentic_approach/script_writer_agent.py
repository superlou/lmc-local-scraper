from google import genai
import pandas as pd
from pydantic import BaseModel

from agent_util import build_prompt


class Opening(BaseModel):
    text: str


class Closing(BaseModel):
    text: str


class Story(BaseModel):
    text: str
    image_desc: str
    music_desc: str


class ScriptResult(BaseModel):
    opening: str
    stories: list[Story]
    closing: str


class ScriptWriterAgent:
    def __init__(self, events: pd.DataFrame):
        self.events = events

    def run(self, llm: genai.Client) -> ScriptResult:
        prompt = build_prompt(
            "agentic_approach/prompts/script_writer.txt",
            date="9/20/25",
            csv=self.events.to_csv(),
        )

        response = llm.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=ScriptResult,
            ),
        )

        return response.parsed
