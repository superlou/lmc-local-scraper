import json
import os
from argparse import Namespace
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path

import jinja2
from loguru import logger

from events_ai.mailer import Mailer


class StepStatus(Enum):
    UNSELECTED = "unselected"
    INCOMPLETE = "incomplete"
    DONE = "done"


@dataclass
class Overview:
    working_dir: Path
    today: date
    args: Namespace
    do_check: StepStatus = StepStatus.UNSELECTED
    do_research: StepStatus = StepStatus.UNSELECTED
    do_script: StepStatus = StepStatus.UNSELECTED
    do_storyboard: StepStatus = StepStatus.UNSELECTED
    do_film: StepStatus = StepStatus.UNSELECTED
    do_produce: StepStatus = StepStatus.UNSELECTED
    do_create_post: StepStatus = StepStatus.UNSELECTED
    do_site_db: StepStatus = StepStatus.UNSELECTED
    exception: Exception | None = None
    traceback: str | None = None
    started_at: datetime = datetime.now()
    finished_at: datetime | None = None
    token_usage: list[dict] | None = None
    token_usage_total: int = 0
    omitted_events: list[dict] | None = None
    location_review_events: list[dict] | None = None
    event_omissions_assessed: bool = False
    email_report_note: str = ""


def try_to_attach(mailer: Mailer, file_path: Path, filename: str, mode: str = "r"):
    try:
        mailer.attach(open(file_path, mode), filename)
    except FileNotFoundError:
        logger.warning(f"Failed to find file to attach as {filename}")


def send_overview_email(
    destination: str, args, today: date, working_dir: Path, overview: Overview
):
    overview.token_usage = []
    overview.omitted_events = []
    overview.location_review_events = []
    usage_path = working_dir / "gemini_token_usage.jsonl"
    try:
        with usage_path.open(encoding="utf-8") as usage_file:
            for line in usage_file:
                if line.strip():
                    overview.token_usage.append(json.loads(line))
    except (OSError, ValueError):
        overview.email_report_note = (
            "Gemini did not provide a readable usage record for this loadup."
        )
    overview.token_usage_total = sum(
        int(row.get("total_tokens", 0)) for row in overview.token_usage
    )

    if overview.do_site_db in (StepStatus.DONE, StepStatus.INCOMPLETE):
        try:
            report = json.loads((working_dir / "site_db_run_report.json").read_text())
            if not isinstance(report, dict):
                raise ValueError("Site database report must be a JSON object")
            overview.omitted_events = report.get("event_omissions", [])
            overview.location_review_events = report.get("location_review_events", [])
            overview.event_omissions_assessed = True
        except (OSError, ValueError, KeyError):
            overview.email_report_note = (
                overview.email_report_note
                + " Site database omission details were unavailable."
            ).strip()
    else:
        overview.email_report_note = (
            overview.email_report_note
            + " Site database was not run; event omissions were not assessed."
        ).strip()

    mailer = Mailer("gen-ai-bot@lmc-tv.org", os.environ["GMAIL_USER_APP_PASSWORD"])
    mailer.subject = build_subject(overview)
    mailer.body = build_body(overview)
    try_to_attach(mailer, working_dir / "log.txt", f"log_{today}.txt")
    try_to_attach(mailer, working_dir / "events.csv", f"events_{today}.csv")
    try_to_attach(
        mailer, working_dir / "research_tokens.csv", f"research_tokens_{today}.csv"
    )
    try_to_attach(mailer, working_dir / "script.json", f"script_{today}.json")
    try_to_attach(mailer, working_dir / "storyboard.json", f"storyboard_{today}.json")
    try_to_attach(mailer, working_dir / "video.mp4", f"video_{today}.mp4", "rb")
    try_to_attach(mailer, working_dir / "post.txt", f"post_{today}.txt")
    try_to_attach(mailer, working_dir / "site_db.json", f"site_db_{today}.json")
    try_to_attach(
        mailer,
        working_dir / "site_db_run_report.json",
        f"site_db_run_report_{today}.json",
    )
    try_to_attach(
        mailer,
        working_dir / "gemini_token_usage.jsonl",
        f"gemini_token_usage_{today}.jsonl",
    )
    mailer.send(destination)


def build_subject(overview: Overview) -> str:
    if not overview.exception:
        return f"✅ AI events bot finished - {overview.working_dir}"
    else:
        return f"⚠️ AI events bot failed - {overview.working_dir}"


def build_body(overview: Overview) -> str:
    env = jinja2.Environment(loader=jinja2.PackageLoader("events_ai", "assets"))
    template = env.get_template("overview.html.jinja2")
    return template.render(overview=overview)
