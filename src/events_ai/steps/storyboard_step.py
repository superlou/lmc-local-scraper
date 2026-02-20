import os
from importlib.abc import Traversable
from pathlib import Path

from fpdf import FPDF
from google import genai
from loguru import logger

from events_ai.steps.pipeline_step import PipelineStep

from ..agents.script_writer_agent import ScriptResult
from ..agents.storyboard_agent import StoryboardAgent, StoryboardResult


class StoryboardStep(PipelineStep):
    def __init__(
        self, storyboard_path: Path, script_path: Path, assets_dir: Traversable
    ):
        self.storyboard_path = storyboard_path
        self.script_path = script_path
        self.assets_dir = assets_dir

    @property
    def done(self) -> bool:
        return self.storyboard_path.exists()

    def run(self, width, height):
        llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        script = ScriptResult.model_validate_json(open(self.script_path).read())
        logger.info(f"Loaded script from {self.script_path}")

        aspect_ratio = width / height

        if abs(percent_error(aspect_ratio, 16 / 9)) < 2.0:
            gen_aspect_ratio = "16:9"
        elif abs(percent_error(aspect_ratio, 9 / 16)) < 2.0:
            gen_aspect_ratio = "9:16"
        else:
            raise StoryboardDimensionsInvalid("Could not generate storyboard")

        storyboard = StoryboardAgent(
            script,
            str(self.assets_dir / "studio_backdrop2.jpg"),
            self.script_path.parent,
            gen_aspect_ratio,
        )
        result = storyboard.run(llm)

        with open(self.storyboard_path, "w") as storyboard_file:
            storyboard_file.write(result.model_dump_json(indent=4))

        logger.info(f"Wrote storyboard to {self.storyboard_path}")

        storyboard_pdf_path = self.storyboard_path.with_suffix(".pdf")
        storyboard_to_pdf(
            StoryboardResult.model_validate_json(open(self.storyboard_path).read()),
            self.assets_dir,
            storyboard_pdf_path,
        )

        logger.info(f"Created storyboard PDF at {storyboard_pdf_path}")


class StoryboardDimensionsInvalid(Exception):
    pass


def percent_error(actual: float, expected: float) -> float:
    return (actual - expected) / expected * 100.0


def storyboard_to_pdf(storyboard: StoryboardResult, assets: Traversable, output: Path):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("NotoSans", "", assets / "NotoSans-Regular.ttf")
    pdf.set_font("NotoSans", size=12)

    for take in storyboard.takes:
        pdf.image(take.frame, h=40)
        pdf.multi_cell(0, 10, text=take.text, new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(output))
