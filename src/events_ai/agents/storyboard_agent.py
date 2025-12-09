from io import BytesIO
from pathlib import Path

from google import genai
from loguru import logger
from PIL import Image
from pydantic import BaseModel

from .agent_util import build_prompt
from .script_writer_agent import ScriptResult


class Take(BaseModel):
    id: int
    text: str
    frame: str


class StoryboardResult(BaseModel):
    takes: list[Take]


class StoryboardAgent:
    def __init__(self, script: ScriptResult, base_image_path: str, gen_dir: Path):
        self.script = script
        self.base_image_path = base_image_path
        self.base_image = Image.open(base_image_path)
        self.gen_dir = gen_dir

    def run(self, llm: genai.Client) -> StoryboardResult:
        result = StoryboardResult(takes=[])

        take_id = 0

        result.takes.append(
            Take(id=take_id, text=self.script.opening, frame=self.base_image_path)
        )

        for i, story in enumerate(self.script.stories):
            frame_path = str(self.gen_dir / f"generated_frame_{i + 1}.jpg")
            logger.info(
                f"Generating frame {i + 1}/{len(self.script.stories)}: {frame_path}"
            )
            self.generate_frame(llm, story.image_desc, frame_path)
            take_id += 1
            result.takes.append(Take(id=take_id, text=story.text, frame=frame_path))

        take_id += 1
        result.takes.append(
            Take(id=take_id, text=self.script.closing, frame=self.base_image_path)
        )
        return result

    def generate_frame(self, llm, background_desc: str, frame_path: str):
        prompt = build_prompt("background.txt", background_description=background_desc)
        response = llm.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_modalities=["Image"],
                image_config=genai.types.ImageConfig(aspect_ratio="16:9"),
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.text is not None:
                logger.info("Got text: " + part.text)
            elif part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                image.save(frame_path)

    def generate_frame_from_base(self, llm, background_desc: str, frame_path: str):
        prompt = build_prompt("frame.txt", background_description=background_desc)

        response = llm.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=[prompt, self.base_image],
            config=genai.types.GenerateContentConfig(
                response_modalities=["Image"],
                image_config=genai.types.ImageConfig(aspect_ratio="16:9"),
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.text is not None:
                logger.info("Got text: " + part.text)
            elif part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                image.save(frame_path)
