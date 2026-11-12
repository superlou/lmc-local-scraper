import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from multiprocessing import Value
from pathlib import Path

import pandas as pd
from loguru import logger
from pydantic import BaseModel, Field

from events_ai import image_tools
from events_ai.agents.prompt import build_prompt
from events_ai.aws import AWS
from events_ai.services.gemini_chat_service import GeminiChatService
from events_ai.services.gemini_image_service import GeminiImageService
from events_ai.steps.pipeline_step import PipelineStep


def when_to_datetime(when: str) -> datetime:
    """
    For whatever reason, when is similar to ISO8601 but missing the T. It
    may be a datetime or simply a date. This function is expected to throw
    exceptions if it fails to parse `when`.
    """
    return datetime.fromisoformat(when.replace(" ", "T"))


def when_is_between(when: str, start: date, finish: date) -> bool:
    try:
        when_date = when_to_datetime(when).date()
        return when_date >= start and when_date <= finish
    except Exception:
        return False


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
        df = pd.read_csv(self.events_path, index_col="id")
        num_all_events = len(df)
        start = today + timedelta(days=-7)
        finish = today + timedelta(days=21)
        df = df[df.when.apply(lambda w: when_is_between(w, start, finish))]

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

        logger.info(
            f"Starting to build Site DB from {len(df)} of {num_all_events} events"
        )

        site_db = SiteDB()
        chat = GeminiChatService("gemini-3.5-flash-lite")

        # Standardize and analyze all events
        prompt = build_prompt("site_db.txt.jinja2", csv=df.to_csv(), today=today)
        result = chat.message(prompt, SiteDBEventsResult)
        site_db.events = result.events

        # Choose featured events
        prompt = build_prompt(
            "site_db_feature.txt.jinja2",
            num_to_feature=num_featured_events,
            recently_featured=recent_featured_events,
            today=today,
        )
        logger.info(f"Choosing events to feature. Prompt: {prompt}")
        result = chat.message(prompt, SiteDBFeatureResult)
        site_db.featured = result.featured_events

        # Generate background images
        with ThreadPoolExecutor(max_workers=3) as executor:
            executor.map(self.generate_background_image, site_db.featured)

        # Save results
        with open(self.site_db_path, "w") as site_db_file:
            site_db_file.write(site_db.model_dump_json(indent=4))

        logger.info(f"Site DB written to {self.site_db_path}")

        # Upload to AWS
        bucket = "lmc-local-events-data"
        dest = "public/data.json"
        AWS().upload_to_s3(self.site_db_path, bucket, dest)
        logger.info(f"Uploaded {self.site_db_path} to bucket {bucket}, {dest}")

    def generate_background_image(self, featured_event: "FeaturedEvent"):
        id = featured_event.id
        image_path = self.events_path.parent / f"site_db_featured_{id}.jpg"
        logger.info(
            f"Generating background for featured event {id}, {featured_event.background_desc}: {image_path}"
        )
        prompt = build_prompt(
            "site_db_feature_background.txt.jinja2",
            background_description=featured_event.background_desc,
        )

        GeminiImageService().generate(prompt, image_path)
        image_tools.compress(image_path, 50)
        featured_event.background_b64 = image_tools.to_b64_url(image_path)


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
