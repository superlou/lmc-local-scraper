import os
from datetime import date
from pathlib import Path

from google import genai
from loguru import logger

from ..agents.script_writer_agent import ScriptResult
from ..agents.social_media_writer_agent import SocialMediaWriterAgent
from .pipeline_step import PipelineStep


class WritePostStep(PipelineStep):
    def __init__(self, post_path: Path, script_path):
        self.post_path = post_path
        self.script_path = script_path

    @property
    def done(self) -> bool:
        return self.post_path.exists()

    def run(self, today: date):
        llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        script = ScriptResult.model_validate_json(open(self.script_path).read())

        writer = SocialMediaWriterAgent(script, today)
        post_text = writer.run(llm)

        with open(self.post_path, "w") as post_file:
            post_file.write(post_text)

        logger.info(f"Post written to {self.post_path}")
