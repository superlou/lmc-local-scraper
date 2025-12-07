import json
import os
import time
from datetime import date, datetime
from glob import glob
from pathlib import Path

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta
from fpdf import FPDF
from google import genai
from loguru import logger
from moviepy import CompositeVideoClip, VideoFileClip, concatenate_videoclips
from moviepy.video.VideoClip import TextClip
from pydantic import ValidationError
from requests.exceptions import JSONDecodeError

from agents.event_list_agent import EventListAgent, EventsResult
from agents.film_agent import FilmAgent
from agents.flat_event_page_agent import FlatEventPageAgent
from agents.heygen_client import HeyGenClient
from agents.script_writer_agent import ScriptResult, ScriptWriterAgent
from agents.storyboard_agent import StoryboardAgent, StoryboardResult
from titler.titler import Titler


class Producer:
    def __init__(self, working_dir: Path):
        self.path = working_dir

    def research_events(self, targets, filter: list[str], today: date):
        llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        all_targets = targets
        logger.info(f"Found {len(all_targets)} research targets")

        if filter and len(filter) > 0:
            targets = {
                target: config
                for target, config in all_targets.items()
                if target in filter
            }
        else:
            targets = all_targets

        logger.info(f"Running {len(targets)} research targets")

        for target, config in targets.items():
            if config["agent"] == "EventListAgent":
                agent = EventListAgent(
                    config["url"],
                    use_selenium=config.get("use_selenium", False),
                    start_url_params=config.get("url_params", None),
                )
            elif config["agent"] == "FlatEventPageAgent":
                agent = FlatEventPageAgent(
                    config["url"], use_selenium=config.get("use_selenium", False)
                )
            else:
                logger.warning(
                    f"Target {target} specified unknown agent {config['agent']}"
                )
                continue

            logger.info(f"Researching {target}")
            finish = today + relativedelta(months=1)
            result = agent.run(llm, today, finish)
            df = result_to_df(result)
            df["organization"] = config["organization"]
            logger.info(f"Found {len(df)} events from {target}", tokens=agent.tokens)
            df.to_csv(self.path / f"events_{target}.csv")

        events_files = self.path.glob("events_*.csv")
        df = pd.concat([pd.read_csv(filename) for filename in events_files])

        events_path = self.path / "events.csv"
        df.to_csv(events_path)
        logger.info(f"Collected {len(df)} events into {events_path}")

    def write_script(self, today: date, num_events: int):
        llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        df = pd.read_csv(self.path / "events.csv")
        logger.info(f"Loaded {len(df)} events to write script.")
        script_writer = ScriptWriterAgent(df, today, num_events)
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

        storyboard = StoryboardAgent(script, "assets/studio_background.png", self.path)
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

    def start_clip_jobs(self):
        storyboard_path = self.path / "storyboard.json"

        client = HeyGenClient(os.environ["HEYGEN_API_KEY"])
        quota_response = client.check_quota()
        logger.info("Checked HeyGen quota", response=quota_response)

        storyboard = StoryboardResult.model_validate_json(open(storyboard_path).read())

        for take in storyboard.takes:
            agent = FilmAgent(os.environ["HEYGEN_API_KEY"], take.text, take.frame)
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

    def film_clips(self):
        self.start_clip_jobs()
        self.wait_and_download_clip_jobs()

    def produce_video(self, today: date):
        titler = Titler("assets/titles")
        titler.generate(
            f"tag_bottom_left.html?text={today.strftime('%m/%d/%Y')}",
            5,
            self.path / "frames",
            self.path / "title_intro.webm",
        )

        clip_files = sorted(self.path.glob("clip_*.mp4"))
        logger.info(f"Found {len(clip_files)} clips")

        intro = VideoFileClip(clip_files[0])
        title = VideoFileClip(self.path / "title_intro.webm", has_mask=True)
        intro = CompositeVideoClip([intro, title])

        video = concatenate_videoclips(
            [intro] + [VideoFileClip(clip_file) for clip_file in clip_files[1:]]
        )

        output_path = self.path / "video.mp4"
        logger.info(f"Writing video to {output_path}...")
        video.write_videofile(output_path)
        logger.info(f"Wrote video to {output_path}")


def storyboard_to_pdf(storyboard: StoryboardResult, output: Path):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("NotoSans", "", "assets/NotoSans-Regular.ttf")
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
    except IOError as e:
        logger.error(f"Error saving file from {url} to {filename}")
