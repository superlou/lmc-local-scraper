import base64
import io
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

import pandas as pd
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

        recent_featured_events = []
        for recent_dir in recent_working_dirs:
            try:
                recent_site_db_file = open(recent_dir / "site_db.json")
                recent_site_db = json.load(recent_site_db_file)
                recent_featureds = recent_site_db["featured"]
                for recent_featured in recent_featureds:
                    recent_featured_id = recent_featured["id"]
                    recent_featured_event = next(
                        e
                        for e in recent_site_db["events"]
                        if e["id"] == recent_featured_id
                    )
                    recent_featured_events.append(recent_featured_event)
            except Exception:
                logger.warning(f"Unable to open recent events for {recent_dir}")

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
        prompt = build_prompt(
            "site_db_feature.txt.jinja2",
            csv=df.to_csv(),
            recently_featured=recent_featured_events,
        )
        logger.info(f"Choosing events to feature. Prompt: {prompt}")

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

        # Generate background images
        def image_worker(featured_event: "FeaturedEvent"):
            llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            self.generate_background_image(featured_event, llm)

        with ThreadPoolExecutor(max_workers=3) as executor:
            executor.map(image_worker, site_db.featured)

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

    def generate_background_image(
        self, featured_event: "FeaturedEvent", llm: genai.Client
    ):
        image_path = (
            self.events_path.parent / f"site_db_featured_{featured_event.id}.jpg"
        )
        logger.info(
            f"Generating background for featured event {featured_event.id}, {featured_event.background_desc}: {image_path}"
        )
        prompt = build_prompt(
            "site_db_feature_background.txt.jinja2",
            background_description=featured_event.background_desc,
        )
        self.generate_image(llm, prompt, image_path)

        # Compress
        with Image.open(image_path) as img:
            img.save(image_path, "JPEG", optimize=True, quality=50)

        with Image.open(image_path) as img:
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            featured_event.background_b64 = f"data:image/jpeg;base64,{b64}"

    def generate_image(
        self,
        llm: genai.Client,
        prompt: str,
        frame_path: Path,
        retries: int = 5,
    ):
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
    built_at: datetime | None = datetime.now()
    events: list[SiteDBEvent] = Field(default_factory=list)
    featured: list[FeaturedEvent] = Field(default_factory=list)
