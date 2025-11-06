from openai import OpenAI


class SoraClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key)

    def create_video(self):
        video = self.client.videos.create(
            model="sora-2",
            prompt="Create a wide shot of a sun over a shining waterfall. A futurisitc monorail runs along the top of the waterfall.",
            seconds="4",
        )
        print("Video:", video)
