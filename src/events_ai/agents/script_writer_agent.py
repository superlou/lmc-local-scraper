from datetime import date

import pandas as pd
from google import genai
from pydantic import BaseModel

from .prompt import build_prompt


class Opening(BaseModel):
    text: str


class Closing(BaseModel):
    text: str


class Story(BaseModel):
    text: str
    image_desc: str
    music_desc: str
    title: str
    when: str
    where: str


class ScriptResult(BaseModel):
    opening: str
    stories: list[Story]
    closing: str


class ScriptWriterAgent:
    def __init__(self, events: pd.DataFrame, today: date, num_events: int):
        self.events = events
        self.num_events = num_events
        self.today = today

    def run(self, llm: genai.Client) -> ScriptResult:
        prompt = build_prompt(
            "script_writer.txt.jinja2",
            date=self.today,
            csv=self.events.to_csv(),
            num_events=self.num_events,
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
