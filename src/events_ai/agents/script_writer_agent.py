from datetime import date

import pandas as pd
from google import genai
from loguru import logger
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
    link: str | None
    organization: str


class ScriptResult(BaseModel):
    opening: str
    stories: list[Story]
    closing: str


class ScriptWriterAgent:
    def __init__(
        self,
        events: pd.DataFrame,
        today: date,
        num_events: int,
        recent_scripts: list[ScriptResult],
    ):
        self.events = events
        self.num_events = num_events
        self.today = today
        self.recent_scripts = recent_scripts

    def run(self, llm: genai.Client) -> ScriptResult:
        prompt = build_prompt(
            "script_writer.txt.jinja2",
            date=self.today,
            csv=self.events.to_csv(),
            num_events=self.num_events,
            recent_scripts=self.recent_scripts,
        )

        logger.debug(f"Script writer prompt: {prompt}")

        response = llm.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=ScriptResult,
            ),
        )

        parsed: ScriptResult = response.parsed
        logger.debug(f"Script writer result: {parsed}")
        return parsed
