from datetime import date

from google import genai
from loguru import logger

from events_ai.agents.prompt import build_prompt
from events_ai.agents.script_writer_agent import ScriptResult


class SocialMediaWriterAgent:
    def __init__(self, script: ScriptResult, today: date):
        self.script = script
        self.today = today

    def run(self, llm: genai.Client) -> str:
        prompt = build_prompt(
            "social_media_post.txt.jinja2", script=self.script, date=self.today
        )

        logger.debug(f"Social media writer prompt: {prompt}")

        response = llm.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
            ),
        )

        text = response.text
        logger.debug(f"Social media writer result: {text}")
        return text or ""
