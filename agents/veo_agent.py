import time
from google import genai
from google.genai.types import GenerateVideosConfig


class VeoClient:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def generate_video(self, prompt: str, first_frame: str, output_filename: str):
        config = GenerateVideosConfig(duration_seconds=4)
        operation = self.client.models.generate_videos(
            model="veo-3.1-fast-generate-preview", config=config, prompt=prompt
        )

        while not operation.done:
            print("Waiting for video generation to complete...")
            time.sleep(10)
            operation = self.client.operations.get(operation)

        generated_video = operation.response.generated_videos[0]
        self.client.files.download(file=generated_video.video)
        generated_video.video.save(output_filename)
