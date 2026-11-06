import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

import pandas as pd
from loguru import logger
from pydantic import BaseModel, Field, ValidationError

from events_ai import image_tools
from events_ai.agents.prompt import build_prompt
from events_ai.aws import AWS
from events_ai.services.gemini_chat_service import GeminiChatService
from events_ai.services.gemini_image_service import GeminiImageService
from events_ai.services.service import ServiceGenerationFailed
from events_ai.steps.pipeline_step import PipelineStep


class SiteDBStep(PipelineStep):
    def __init__(self, events_path: Path, site_db_path: Path):
        self.events_path = events_path
        self.site_db_path = site_db_path
        self.report_path = site_db_path.parent / "site_db_run_report.json"
        self.usage_records = []
        self.omitted_events = []
        self.location_review_events = []

    def save_run_report(self, batches=None):
        report = {
            "usage": self.usage_records,
            "event_omissions": self.omitted_events,
            "location_review_events": self.location_review_events,
            "batches": batches or [],
        }
        try:
            self.report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning(f"Unable to save site database email report: {exc}")

    @staticmethod
    def usage_rows(service, stage):
        return [
            {
                "stage": stage,
                "model": use.model,
                "input_tokens": use.input,
                "cached_input_tokens": use.cached,
                "output_tokens": use.output,
                "total_tokens": use.total,
            }
            for use in getattr(service, "usages", [])
        ]

    @staticmethod
    def is_placeholder_link(value):
        if pd.isna(value) or not str(value).strip():
            return False
        try:
            host = (urlparse(str(value)).hostname or "").lower().rstrip(".")
        except ValueError:
            return False
        return host == "example.com" or host.endswith(".example.com")

    @staticmethod
    def duplicate_key(event):
        def clean(value):
            return re.sub(r"\s+", " ", str(value or "").strip()).casefold()

        return clean(event.title), clean(event.when), clean(event.where)

    @property
    def done(self) -> bool:
        return self.site_db_path.exists()

    def run(
        self, today: date, num_featured_events: int, recent_working_dirs: list[Path]
    ):
        df = pd.read_csv(self.events_path, index_col="id")
        batches_report = []
        self.usage_records = []
        self.omitted_events = []
        self.location_review_events = []

        for event_id, event in df.iterrows():
            if self.is_placeholder_link(event.get("link")):
                self.omitted_events.append({
                    "id": int(event_id),
                    "title": str(event.get("event", "")),
                    "reason": "placeholder example.com event link",
                })
            elif self.needs_location_review(event.get("location")):
                self.location_review_events.append({
                    "id": int(event_id),
                    "title": str(event.get("event", "")),
                    "location": str(event.get("location", "")),
                    "reason": "location may be outside the service area; review only",
                })
        if self.omitted_events:
            rejected = {item["id"] for item in self.omitted_events}
            df = df.loc[[int(event_id) not in rejected for event_id in df.index]]
        self.save_run_report(batches_report)

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

        site_db = SiteDB()

        # Standardize and analyze events in at most two smaller requests.
        # Each batch starts a fresh conversation so earlier CSV context is not resent.
        if df.empty:
            raise ValueError("No events available to build the site database")
        if not df.index.is_unique:
            raise ValueError("Input event IDs must be unique")
        batch_count = min(2, len(df))
        for batch_number in range(batch_count):
            start = batch_number * len(df) // batch_count
            finish = (batch_number + 1) * len(df) // batch_count
            batch = df.iloc[start:finish]
            prompt = build_prompt(
                "site_db.txt.jinja2",
                csv=batch.drop(columns=["link", "organization"]).to_csv(),
                today=today,
            )
            model = "gemini-2.5-flash"
            batch_ids = {int(event_id) for event_id in batch.index}
            # The service implementation hash invalidates checkpoints when request behavior changes.
            service_path = Path(__file__).parents[1] / "services/gemini_chat_service.py"
            signature = json.dumps(
                {
                    "version": 1,
                    "model": model,
                    "date": today.isoformat(),
                    "input": batch.to_csv(),
                    "prompt": prompt,
                    "schema": SiteDBEventsResult.model_json_schema(),
                    "service": hashlib.sha256(service_path.read_bytes()).hexdigest(),
                },
                sort_keys=True,
            )
            digest = hashlib.sha256(signature.encode()).hexdigest()
            checkpoint_dir = self.site_db_path.parent / ".site-db-batches"
            checkpoint = checkpoint_dir / f"{digest}.json"
            usage_checkpoint = checkpoint_dir / f"{digest}.usage.json"
            result = None
            batch_usage = []
            cached_usage = []
            if checkpoint.exists():
                try:
                    result = SiteDBEventsResult.model_validate_json(
                        checkpoint.read_text()
                    )
                    self.validate_batch(result, batch_ids)
                    logger.info(f"Reusing saved event batch {batch_number + 1}")
                    if usage_checkpoint.exists():
                        try:
                            cached_usage = json.loads(usage_checkpoint.read_text())
                        except (OSError, ValueError):
                            logger.warning(
                                f"Ignoring invalid usage details for batch {batch_number + 1}"
                            )
                except (OSError, ValueError):
                    logger.warning(
                        f"Ignoring invalid saved event batch {batch_number + 1}"
                    )
                    result = None
            if result is None:
                batch_chat = GeminiChatService(
                    model, stage=f"site_db_batch_{batch_number + 1}"
                )
                try:
                    result = batch_chat.message(prompt, SiteDBEventsResult)
                    batch_usage.extend(
                        self.usage_rows(batch_chat, f"site_db_batch_{batch_number + 1}")
                    )
                except (ValidationError, ServiceGenerationFailed):
                    batch_usage.extend(
                        self.usage_rows(
                            batch_chat, f"site_db_batch_{batch_number + 1}_attempt_1"
                        )
                    )
                    logger.warning(
                        f"Invalid event response for batch {batch_number + 1}; retrying once"
                    )
                    chat = GeminiChatService(
                        model, stage=f"site_db_batch_{batch_number + 1}_retry"
                    )
                    result = chat.message(prompt, SiteDBEventsResult)
                    batch_usage.extend(
                        self.usage_rows(
                            chat, f"site_db_batch_{batch_number + 1}_retry"
                        )
                    )
                self.validate_batch(result, batch_ids)
                checkpoint_dir.mkdir(parents=True, exist_ok=True)
                temporary = None
                try:
                    with NamedTemporaryFile(
                        mode="w",
                        encoding="utf-8",
                        dir=checkpoint_dir,
                        delete=False,
                    ) as saved:
                        temporary = Path(saved.name)
                        saved.write(result.model_dump_json())
                    temporary.replace(checkpoint)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
                try:
                    usage_checkpoint.write_text(
                        json.dumps(batch_usage, indent=2), encoding="utf-8"
                    )
                except OSError as exc:
                    logger.warning(f"Unable to save batch token details: {exc}")
            else:
                batches_report.append(
                    {
                        "batch": batch_number + 1,
                        "status": "checkpoint reused",
                        "tokens_used_this_run": 0,
                        "previous_call_usage": cached_usage,
                    }
                )
            self.usage_records.extend(batch_usage)
            if batch_usage:
                batches_report.append(
                    {
                        "batch": batch_number + 1,
                        "status": "generated",
                        "tokens_used_this_run": sum(
                            row["total_tokens"] for row in batch_usage
                        ),
                        "usage": batch_usage,
                    }
                )
            returned_ids = {event.id for event in result.events}
            for omitted_id in sorted(batch_ids - returned_ids):
                original = df.loc[omitted_id]
                self.omitted_events.append(
                    {
                        "id": int(omitted_id),
                        "title": str(original.get("event", "")),
                        "reason": f"not returned by Gemini batch {batch_number + 1}",
                    }
                )
            for event in result.events:
                original = df.loc[event.id]
                site_db.events.append(
                    SiteDBEvent(
                        **event.model_dump(),
                        link=None if pd.isna(original["link"]) else str(original["link"]),
                        organization=str(original["organization"]),
                    )
                )
            self.save_run_report(batches_report)

        # Remove exact cross-batch repeats locally; this makes no additional model request.
        seen_events = {}
        deduplicated = []
        for event in site_db.events:
            key = self.duplicate_key(event)
            if key in seen_events:
                self.omitted_events.append({
                    "id": event.id,
                    "title": event.title,
                    "reason": f"duplicate of event ID {seen_events[key]}",
                })
            else:
                seen_events[key] = event.id
                deduplicated.append(event)
        site_db.events = deduplicated
        self.save_run_report(batches_report)

        # Choose featured events
        chat = GeminiChatService("gemini-2.5-flash", stage="site_db_featured_events")
        prompt = build_prompt(
            "site_db_feature.txt.jinja2",
            num_to_feature=num_featured_events,
            recently_featured=recent_featured_events,
            today=today,
            events=[
                {
                    "id": event.id,
                    "description": f"{event.title}: {event.why}",
                    "tags": event.tags,
                    "when": event.when,
                    "organization": event.organization,
                }
                for event in site_db.events
            ],
        )
        logger.info(f"Choosing events to feature. Prompt: {prompt}")
        result = chat.message(prompt, SiteDBFeatureResult)
        self.usage_records.extend(self.usage_rows(chat, "site_db_featured_events"))
        self.save_run_report(batches_report)
        event_ids = {event.id for event in site_db.events}
        if any(event.id not in event_ids for event in result.featured_events):
            raise ValueError("Gemini featured an event outside the site database")
        site_db.featured = result.featured_events

        # Generate background images
        with ThreadPoolExecutor(max_workers=3) as executor:
            image_usage = list(executor.map(self.generate_background_image, site_db.featured))
        for event_id, rows in image_usage:
            for row in rows:
                row["stage"] = f"featured_image_event_{event_id}"
            self.usage_records.extend(rows)

        # Save results
        with open(self.site_db_path, "w") as site_db_file:
            site_db_file.write(site_db.model_dump_json(indent=4))

        logger.info(f"Site DB written to {self.site_db_path}")
        self.save_run_report(batches_report)

        # Upload to AWS
        bucket = "lmc-local-events-data"
        dest = "public/data.json"
        AWS().upload_to_s3(self.site_db_path, bucket, dest)
        logger.info(f"Uploaded {self.site_db_path} to bucket {bucket}, {dest}")

    @staticmethod
    def validate_batch(result, batch_ids):
        if any(event.id not in batch_ids for event in result.events):
            raise ValueError("Gemini returned an event outside its batch")
        if len({event.id for event in result.events}) != len(result.events):
            raise ValueError("Gemini returned duplicate event IDs")

    @staticmethod
    def needs_location_review(location):
        text = str(location or "").casefold()
        return any(
            place in text
            for place in ("san francisco", "new york", "washington, dc", "washington dc")
        )

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

        image_service = GeminiImageService(
            stage=f"featured_image_event_{featured_event.id}"
        )
        image_service.generate(prompt, image_path)
        image_tools.compress(image_path, 50)
        featured_event.background_b64 = image_tools.to_b64_url(image_path)
        return featured_event.id, self.usage_rows(
            image_service, f"featured_image_event_{featured_event.id}"
        )


class SiteDBEventDetails(BaseModel):
    id: int
    title: str
    when: str
    where: str
    why: str
    tags: list[str]


class SiteDBEvent(SiteDBEventDetails):
    link: str | None
    organization: str


class SiteDBEventsResult(BaseModel):
    events: list[SiteDBEventDetails]


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
