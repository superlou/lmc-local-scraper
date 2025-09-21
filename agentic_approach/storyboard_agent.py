from io import BytesIO

from google import genai
from PIL import Image
from pydantic import BaseModel

from script_writer_agent import ScriptResult
from agent_util import build_prompt


class Take(BaseModel):
    text: str
    frame: str


class StoryboardResult(BaseModel):
    takes: list[Take]


class StoryboardAgent():
    def __init__(self, script: ScriptResult, base_image_path: str):
        self.script = script
        self.base_image_path = base_image_path
        self.base_image = Image.open(base_image_path)
    
    def run(self, llm: genai.Client) -> StoryboardResult:
        result = StoryboardResult(takes=[])

        result.takes.append(Take(text=self.script.opening, frame=self.base_image_path))

        for i, story in enumerate(self.script.stories):
            frame_path = f"gen/generated_frame_{i+1}.jpg"
            print(f"Generating frame {i + 1}/{len(self.script.stories)}: {frame_path}")
            self.generate_frame(llm, story.image_desc, frame_path)
            result.takes.append(Take(text=story.text, frame=frame_path))    

        result.takes.append(Take(text=self.script.closing, frame=self.base_image_path))
        return result
    
    def generate_frame(self, llm, background_desc: str, frame_path: str):
        prompt = build_prompt(
            "agentic_approach/prompts/frame.txt",
            background_description=background_desc
        )

        response = llm.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=[prompt, self.base_image],
        )

        for part in response.candidates[0].content.parts:
            if part.text is not None:
                print(part.text)
            elif part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                image.save(frame_path)