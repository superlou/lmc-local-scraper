from io import BytesIO

from google import genai
from PIL import Image

from script_writer_agent import ScriptResult

class StoryboardAgent():
    def __init__(self, script: ScriptResult, base_image_path: str):
        self.script = script
        self.base_image = Image.open(base_image_path)
    
    def run(self, llm: genai.Client):
        prompt = "Replace the background with a banana"

        response = llm.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=[prompt, self.base_image],
        )

        for part in response.candidates[0].content.parts:
            if part.text is not None:
                print(part.text)
            elif part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                image.save("gen/generated_image.png")