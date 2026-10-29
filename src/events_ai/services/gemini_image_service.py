import base64
import os
import time
from pathlib import Path

import google.genai
from google.genai.interactions import Interaction
from loguru import logger

from events_ai.services.gemini_chat_service import GeminiServiceUse

from .service import Service, ServiceGenerationFailed


class GeminiImageService(Service):
    def __init__(self, model: str = "gemini-nano-banana-2.1"):
        super().__init__()
        self.llm = google.genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.model = model

    def generate(self, prompt: str, frame_path: Path, retries: int = 5) -> None:
        done = False

        while not done and retries > 0:
            interaction = self.llm.interactions.create(
                model=self.model,
                input=prompt,
                response_format={
                    "type": "image",
                    "mime_type": "image/jpeg",
                    "aspect_ratio": "16:9",
                    "image_size": "1K",
                },
                stream=False,
            )

            if not isinstance(interaction, Interaction):
                time.sleep(1)
                continue

            if (
                interaction.output_image is None
                or interaction.output_image.data is None
            ):
                time.sleep(5)  # todo Exponential back-off
                continue

            with open(frame_path, "wb") as f:
                f.write(base64.b64decode(interaction.output_image.data))

            if interaction.usage is not None:
                use = GeminiServiceUse(self.model, interaction.usage)
                logger.info(use.log_msg)
                self.usages.append(use)

            return

        raise ServiceGenerationFailed()
