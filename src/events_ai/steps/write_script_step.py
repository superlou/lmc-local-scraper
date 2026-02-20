import os
from datetime import date
from pathlib import Path

import pandas as pd
from google import genai
from loguru import logger

from events_ai.steps.pipeline_step import PipelineStep

from ..agents.script_writer_agent import ScriptResult, ScriptWriterAgent


class WriteScriptStep(PipelineStep):
    def __init__(self, script_path: Path, events_path: Path):
        self.script_path = script_path
        self.events_path = events_path

    @property
    def done(self) -> bool:
        return self.script_path.exists()

    def run(self, today: date, num_events: int, recent_working_dirs: list[Path]):
        llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        recent_scripts = [
            ScriptResult.model_validate_json(open(script_path).read())
            for dir in recent_working_dirs
            if (script_path := dir / "script.json").exists()
        ]

        df = pd.read_csv(self.events_path, index_col="id")
        logger.info(f"Loaded {len(df)} events to write script.")
        script_writer = ScriptWriterAgent(df, today, num_events, recent_scripts)
        script = script_writer.run(llm)

        with open(self.script_path, "w") as script_file:
            script_file.write(script.model_dump_json(indent=4))

        logger.info(f"Script written to {self.script_path}")
