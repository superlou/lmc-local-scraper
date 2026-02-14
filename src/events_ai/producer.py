import importlib.resources
import json
import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta
from fpdf import FPDF
from google import genai
from htmlcorder.titler import Titler
from loguru import logger
from moviepy import CompositeVideoClip, VideoFileClip, concatenate_videoclips
from pydantic import ValidationError

from events_ai.agents.research_agent_factory import ResearchAgentFactory
from events_ai.agents.social_media_writer_agent import SocialMediaWriterAgent
from events_ai.phonetic_replacer import PhoneticReplacer

from . import humanize
from .agents.film_agent import FilmAgent
from .agents.gemini_event_research_agent import EventsResult
from .agents.heygen_client import HeyGenClient
from .agents.script_writer_agent import ScriptResult, ScriptWriterAgent
from .agents.storyboard_agent import StoryboardAgent, StoryboardResult, Take

ASSETS_DIR = importlib.resources.files(__name__) / "assets"


class Producer:
    def __init__(self, working_dir: Path, dimensions: tuple[float, float]):
        self.path = working_dir
        self.dimensions = dimensions

    def research_events(self, targets, today: date, filter: list[str] | None = None):
        llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        finish = today + relativedelta(months=1)

        all_targets = targets
        logger.info(f"Found {len(all_targets)} research targets")

        if filter is not None and len(filter) > 0:
            targets = {
                target: config
                for target, config in all_targets.items()
                if target in filter
            }
        else:
            targets = all_targets

        logger.info(f"Running {len(targets)} research targets")

        for target, config in targets.items():
            try:
                agent = ResearchAgentFactory.build(llm, today, finish, **config)
            except ValueError as exc:
                logger.warning(f"Target {target} skipped: {exc}")
                continue

            try:
                logger.info(f"Researching {target}")
                result = agent.run()
                df = result_to_df(result)
                df["organization"] = config["organization"]
                logger.info(
                    f"Found {len(df)} events from {target}", tokens=agent.tokens
                )
                df.to_csv(self.path / f"events_{target}.csv", index_label="id")
            except Exception as err:
                logger.warning(f"Exception researching {target}: {err}")

        events_files = self.path.glob("events_*.csv")
        df = pd.concat(
            [pd.read_csv(filename, index_col="id") for filename in events_files],
            ignore_index=True,
        )

        events_path = self.path / "events.csv"
        df.to_csv(events_path, index_label="id")
        logger.info(f"Collected {len(df)} events into {events_path}")

    def write_script(
        self, today: date, num_events: int, recent_working_dirs: list[Path]
    ):
        llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        recent_scripts = [
            ScriptResult.model_validate_json(open(script_path).read())
            for dir in recent_working_dirs
            if (script_path := dir / "script.json").exists()
        ]

        df = pd.read_csv(self.path / "events.csv", index_col="id")
        logger.info(f"Loaded {len(df)} events to write script.")
        script_writer = ScriptWriterAgent(df, today, num_events, recent_scripts)
        script = script_writer.run(llm)

        script_path = self.path / "script.json"

        with open(script_path, "w") as script_file:
            script_file.write(script.model_dump_json(indent=4))

        logger.info(f"Script written to {script_path}")

    def make_storyboard(self):
        llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        script_path = self.path / "script.json"
        script = ScriptResult.model_validate_json(open(script_path).read())
        logger.info(f"Loaded script from {script_path}")

        aspect_ratio = self.dimensions[0] / self.dimensions[1]

        if abs(percent_error(aspect_ratio, 16 / 9)) < 2.0:
            gen_aspect_ratio = "16:9"
        elif abs(percent_error(aspect_ratio, 9 / 16)) < 2.0:
            gen_aspect_ratio = "9:16"
        else:
            raise ProducerDimensionsInvalid("Could not generate storyboard")

        storyboard = StoryboardAgent(
            script,
            str(ASSETS_DIR / "studio_backdrop2.jpg"),
            self.path,
            gen_aspect_ratio,
        )
        result = storyboard.run(llm)

        storyboard_path = self.path / "storyboard.json"

        with open(storyboard_path, "w") as storyboard_file:
            storyboard_file.write(result.model_dump_json(indent=4))

        logger.info(f"Wrote storyboard to {storyboard_path}")

        storyboard_pdf_path = self.path / "storyboard.pdf"

        storyboard_to_pdf(
            StoryboardResult.model_validate_json(open(storyboard_path).read()),
            storyboard_pdf_path,
        )

        logger.info(f"Created storyboard PDF at {storyboard_path}")

    def start_clip_jobs(self, takes: list[Take], path: Path):
        client = HeyGenClient(os.environ["HEYGEN_API_KEY"])
        quota_response = client.check_quota()
        logger.info(f"Checked HeyGen quota: {quota_response}")

        for take in takes:
            title = f"Around Town, {path}, Take {take.id}"
            agent = FilmAgent(client, take.text, take.frame, title)
            video_id = agent.run()

            clip_job = {
                "clip": take.id,
                "processor": "HeyGen Avatar V2",
                "video_id": video_id,
                "done": False,
                "text": take.text,
                "frame": take.frame,
                "url": "",
            }
            clip_job_path = self.path / f"clip_{take.id}.txt"
            json.dump(clip_job, open(clip_job_path, "w"), indent=4)

            logger.info(f"Started clip job {video_id} with info in {clip_job_path}")

    def wait_and_download_clip_jobs(self):
        client = HeyGenClient(os.environ["HEYGEN_API_KEY"])
        wait_for_jobs = True

        while wait_for_jobs:
            wait_for_jobs = False
            clip_job_paths = sorted(self.path.glob("clip_*.txt"))

            for clip_job_path in clip_job_paths:
                clip_job = json.load(open(clip_job_path))
                clip_path = self.path / f"clip_{clip_job['clip']}.mp4"
                video_id = clip_job["video_id"]

                if clip_job["done"] and Path(clip_path).exists():
                    continue

                try:
                    response = client.get_video_status(video_id)

                    status = response.data["status"]
                    video_url = response.data["video_url"]
                    logger.info(f"Clip {clip_job['clip']}: {status}")
                    if status == "completed":
                        clip_job["done"] = True
                        clip_job["url"] = video_url
                        logger.info(f"Clip job {clip_job['clip']} finished")
                        json.dump(clip_job, open(clip_job_path, "w"), indent=4)

                        logger.info(
                            f"Downloading clip {clip_job['clip']} from {video_url} to {clip_path}"
                        )
                        download_file(video_url, clip_path)
                    else:
                        wait_for_jobs = True
                except ValidationError:
                    pass

            if wait_for_jobs:
                time.sleep(10)

    def film_clips(self, takes_filter: list[int] | None = None):
        storyboard_path = self.path / "storyboard.json"
        storyboard = StoryboardResult.model_validate_json(open(storyboard_path).read())
        phonetic_replacer = PhoneticReplacer(
            json.loads((ASSETS_DIR / "heygen_pronunciation.json").read_text())
        )

        takes = [
            take
            for take in storyboard.takes
            if takes_filter is None or take.id in takes_filter
        ]

        for take in takes:
            take.text = phonetic_replacer.replace(take.text)

        self.start_clip_jobs(takes, self.path)
        self.wait_and_download_clip_jobs()

    def produce_video(self, today: date):
        titler = Titler(ASSETS_DIR / "titles")

        storyboard_path = self.path / "storyboard.json"
        storyboard = StoryboardResult.model_validate_json(open(storyboard_path).read())

        clips = []

        # Add graphics to intro
        intro = VideoFileClip(self.path / f"clip_{storyboard.takes[0].id}.mp4")
        props = {
            "title": "Around Town with LMC",
            "subtitle": "For " + humanize.long_date(today),
            "duration": intro.duration,
        }
        url = "intro_outro.html?" + "&".join([f"{k}={v}" for k, v in props.items()])
        titler.generate(
            url,
            intro.duration,
            self.path / "frames_intro",
            self.path / "title_intro.webm",
            frame_rate=25,
        )
        title = VideoFileClip(self.path / "title_intro.webm", has_mask=True)
        clips.append(CompositeVideoClip([intro, title]))

        # Add graphics to event clips
        for take in storyboard.takes[1:-1]:
            clip = VideoFileClip(self.path / f"clip_{take.id}.mp4")
            props = {
                "name": take.title,
                "when": take.when,
                "where": take.where,
                "duration": clip.duration,
            }
            url = "event_info.html?" + "&".join([f"{k}={v}" for k, v in props.items()])
            take_id = Path(clip.filename).stem

            titler.generate(
                url,
                clip.duration,
                self.path / f"frames_{take_id}",
                self.path / f"title_{take_id}.webm",
                frame_rate=25,
            )

            title = VideoFileClip(self.path / f"title_{take_id}.webm", has_mask=True)
            clips.append(CompositeVideoClip([clip, title]))

        # Add outro
        outro = VideoFileClip(self.path / f"clip_{storyboard.takes[-1].id}.mp4")
        props = {
            "title": "Thanks for Watching",
            "subtitle": "See you tomorrow!",
            "duration": outro.duration,
        }
        url = "intro_outro.html?" + "&".join([f"{k}={v}" for k, v in props.items()])
        titler.generate(
            url,
            outro.duration,
            self.path / "frames_outro",
            self.path / "title_outro.webm",
            frame_rate=25,
        )
        title = VideoFileClip(self.path / "title_outro.webm", has_mask=True)
        clips.append(CompositeVideoClip([outro, title]))

        # Concatenate all titled clips
        video = concatenate_videoclips(clips)
        output_path = self.path / "video.mp4"
        logger.info(f"Writing video to {output_path}...")
        video.write_videofile(output_path, audio_codec="aac")
        logger.info(f"Wrote video to {output_path}")

    def write_social_media_post(self, today: date):
        llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        script_path = self.path / "script.json"
        script = ScriptResult.model_validate_json(open(script_path).read())

        writer = SocialMediaWriterAgent(script, today)
        post_text = writer.run(llm)

        post_path = self.path / "post.txt"

        with open(post_path, "w") as post_file:
            post_file.write(post_text)

        logger.info(f"Post written to {post_path}")


class ProducerDimensionsInvalid(Exception):
    pass


def storyboard_to_pdf(storyboard: StoryboardResult, output: Path):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("NotoSans", "", ASSETS_DIR / "NotoSans-Regular.ttf")
    pdf.set_font("NotoSans", size=12)

    for take in storyboard.takes:
        pdf.image(take.frame, h=40)
        pdf.multi_cell(0, 10, text=take.text, new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(output))


def result_to_df(result: EventsResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event": event.title,
                "link": event.link,
                "description": event.description,
                "when": event.when,
                "location": event.location,
                "price": event.price,
                "target_age": ", ".join(event.target_age),
            }
            for event in result.events
        ]
    )


def download_file(url: str, filename: str | Path):
    try:
        response = requests.get(url, stream=True)
        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading file from {url} to {filename}")
        logger.error(e)
    except IOError as e:
        logger.error(f"Error saving file from {url} to {filename}")
        logger.error(e)


def percent_error(actual: float, expected: float) -> float:
    return (actual - expected) / expected * 100.0
