from openai import OpenAI
from openai.types import Video


class SoraClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key)

    def create_video(self, prompt) -> Video:
        video = self.client.videos.create(
            model="sora-2",
            prompt=prompt,
            seconds="4",
        )
        return video

    def list_videos(self) -> list[Video]:
        return list(self.client.videos.list())

    def get_video_by_id(self, id: str) -> Video:
        return self.client.videos.retrieve(id)

    def download_video(self, id: str, output_file: str):
        response = self.client.videos.download_content(id)
        with open(output_file, "wb") as f:
            f.write(response.read())
