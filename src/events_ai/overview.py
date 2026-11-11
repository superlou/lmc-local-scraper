import os
from argparse import Namespace
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path

import jinja2
import pandas as pd
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
    org_events: dict = field(default_factory=dict)


def try_to_attach(mailer: Mailer, file_path: Path, filename: str, mode: str = "r"):
    try:
        mailer.attach(open(file_path, mode), filename)
    except FileNotFoundError:
        logger.warning(f"Failed to find file to attach as {filename}")


def send_overview_email(
    destination: str, args, today: date, working_dir: Path, overview: Overview
):
    mailer = Mailer("gen-ai-bot@lmc-tv.org", os.environ["GMAIL_USER_APP_PASSWORD"])
    mailer.subject = build_subject(overview)

    events_path = working_dir / "events.csv"

    try:
        overview.org_events = (
            pd.read_csv(events_path).groupby("organization").size().to_dict()
        )
    except Exception:
        pass

    mailer.body = build_body(overview)
    try_to_attach(mailer, working_dir / "log.txt", f"log_{today}.txt")
    try_to_attach(mailer, events_path, f"events_{today}.csv")
    try_to_attach(
        mailer, working_dir / "research_tokens.csv", f"research_tokens_{today}.csv"
    )
    try_to_attach(mailer, working_dir / "script.json", f"script_{today}.json")
    try_to_attach(mailer, working_dir / "storyboard.json", f"storyboard_{today}.json")
    try_to_attach(mailer, working_dir / "video.mp4", f"video_{today}.mp4", "rb")
    try_to_attach(mailer, working_dir / "post.txt", f"post_{today}.txt")
    try_to_attach(mailer, working_dir / "site_db.json", f"site_db_{today}.json")
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
