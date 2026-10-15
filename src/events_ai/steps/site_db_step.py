import base64
import io
import os
from datetime import date
from pathlib import Path

import boto3
import pandas as pd
from cloudflare import Cloudflare
from google import genai
from loguru import logger
from PIL import Image
from pydantic import BaseModel, Field

from events_ai.agents.prompt import build_prompt
from events_ai.aws import AWS
from events_ai.steps.pipeline_step import PipelineStep


class SiteDBStep(PipelineStep):
    def __init__(self, events_path: Path, site_db_path: Path):
        self.events_path = events_path
        self.site_db_path = site_db_path

    @property
    def done(self) -> bool:
        return self.site_db_path.exists()

    def run(
        self, today: date, num_featured_events: int, recent_working_dirs: list[Path]
    ):
        llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        df = pd.read_csv(self.events_path, index_col="id")

        # todo Use recent featured events

        logger.info(f"Starting to build Site DB from {len(df)} events")

        # Standardize and analyze all events
        prompt = build_prompt(
            "site_db.txt.jinja2",
            csv=df.to_csv(),
        )

        site_db = SiteDB()
        chat = llm.chats.create(model="gemini-2.5-flash")

        response = chat.send_message(
            message=prompt,
            config=genai.types.GenerateContentConfig(
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=SiteDBEventsResult,
            ),
        )

        match response.parsed:
            case SiteDBEventsResult() as site_db_events_result:
                site_db.events = site_db_events_result.events

        # Choose featured events
        logger.info("Choosing events to feature.")

        prompt = build_prompt(
            "site_db_feature.txt.jinja2",
            csv=df.to_csv(),
        )

        response = chat.send_message(
            message=prompt,
            config=genai.types.GenerateContentConfig(
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=SiteDBFeatureResult,
            ),
        )

        match response.parsed:
            case SiteDBFeatureResult() as site_db_feature_result:
                site_db.featured = site_db_feature_result.featured_events

        # Generate images
        for featured_event in site_db.featured:
            frame_path = (
                self.events_path.parent / f"site_db_featured_{featured_event.id}.jpg"
            )
            logger.info(
                f"Generating background for featured event {featured_event.id}, {featured_event.background_desc}: {frame_path}"
            )
            self.generate_bg(llm, featured_event.background_desc, frame_path)

            with Image.open(frame_path) as img:
                img.save(frame_path, "JPEG", optimize=True, quality=65)

            with Image.open(frame_path) as img:
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG")
                b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                featured_event.background_b64 = f"data:image/jpeg;base64,{b64}"

        # Save results
        with open(self.site_db_path, "w") as site_db_file:
            site_db_file.write(site_db.model_dump_json(indent=4))

        logger.info(f"Site DB written to {self.site_db_path}")

        # Upload to AWS
        aws = AWS()
        bucket = "lmc-local-events-data"
        dest = "public/data.json"
        aws.upload_to_s3(self.site_db_path, bucket, dest)
        logger.info(f"Uploaded {self.site_db_path} to bucket {bucket}, {dest}")

    def generate_bg(
        self,
        llm: genai.Client,
        background_desc: str,
        frame_path: Path,
        retries: int = 5,
    ):
        prompt = build_prompt(
            "site_db_feature_background.txt.jinja2",
            background_description=background_desc,
        )

        done = False

        while not done and retries > 0:
            interaction = llm.interactions.create(
                model="gemini-nano-banana-2.1",
                input=prompt,
                response_format={
                    "type": "image",
                    "mime_type": "image/jpeg",
                    "aspect_ratio": "16:9",
                    "image_size": "1K",
                },
            )

            with open(frame_path, "wb") as f:
                f.write(base64.b64decode(interaction.output_image.data))

            # todo Handle errors and retry
            return

            candidates = response.candidates or []

            if len(candidates) < 1:
                logger.warning(
                    f"Image generation had no candidates. Waiting. Retries left: {retries}"
                )

                if retries > 0:
                    retries -= 1
                    time.sleep(5)
                    continue
                else:
                    raise StoryboardImageGenerationError()

            candidate = candidates[0]
            if candidate.finish_reason == FinishReason.NO_IMAGE:
                logger.warning(
                    f"Image generation had no image. Waiting. Retries left: {retries}"
                )

                if retries > 0:
                    retries -= 1
                    time.sleep(5)
                    continue
                else:
                    raise StoryboardImageGenerationError()

            done = True

        for part in candidate.content.parts:
            if part.text is not None:
                logger.info("Got text: " + part.text)
            elif part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                image.save(frame_path)


class SiteDBEvent(BaseModel):
    id: int
    title: str
    when: str
    where: str
    why: str
    tags: list[str]
    link: str | None
    organization: str


class SiteDBEventsResult(BaseModel):
    events: list[SiteDBEvent]


class FeaturedEvent(BaseModel):
    id: int
    why: str
    background_desc: str
    background_b64: str = ""


class SiteDBFeatureResult(BaseModel):
    featured_events: list[FeaturedEvent]


class SiteDB(BaseModel):
    events: list[SiteDBEvent] = Field(default_factory=list)
    featured: list[FeaturedEvent] = Field(default_factory=list)
