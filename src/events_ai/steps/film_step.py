import json
import os
import time
from importlib.abc import Traversable
from pathlib import Path
from typing import Generator

import requests
from loguru import logger
from pydantic import ValidationError

from ..agents.film_agent import FilmAgent
from ..agents.heygen_client import HeyGenClient
from ..agents.storyboard_agent import StoryboardResult, Take
from ..phonetic_replacer import PhoneticReplacer
from ..steps.pipeline_step import PipelineStep


class FilmStep(PipelineStep):
    def __init__(self, clip_path: Path, storyboard_path: Path, assets_dir: Traversable):
        self.clip_path = clip_path
        self.storyboard_path = storyboard_path
        self.assets_dir = assets_dir

    @property
    def done(self) -> bool:
        storyboard = StoryboardResult.model_validate_json(
            open(self.storyboard_path).read()
        )
        clip_paths = [self.clip_path_for(take.id) for take in storyboard.takes]
        return all(path.exists() for path in clip_paths)

    def clip_path_for(self, take: int | str) -> Path:
        stem = self.clip_path.stem
        suffix = self.clip_path.suffix
        return self.clip_path.parent / f"{stem}_{take}{suffix}"

    def clip_job_path_for(self, take: int | str) -> Path:
        stem = self.clip_path.stem
        return self.clip_path.parent / f"{stem}_{take}.txt"

    def clip_jobs_glob(self) -> Generator[Path, None, None]:
        return self.clip_path.parent.glob(
            self.clip_path_for("*").with_suffix(".txt").name
        )

    def run(self, episode: str, takes_filter: list[int] | None = None):
        storyboard = StoryboardResult.model_validate_json(
            open(self.storyboard_path).read()
        )
        phonetic_replacer = PhoneticReplacer(
            json.loads((self.assets_dir / "heygen_pronunciation.json").read_text())
        )

        takes = [
            take
            for take in storyboard.takes
            if takes_filter is None or take.id in takes_filter
        ]

        for take in takes:
            take.text = phonetic_replacer.replace(take.text)

        self.start_clip_jobs(takes, episode)
        self.wait_and_download_clip_jobs()

    def start_clip_jobs(self, takes: list[Take], episode: str):
        client = HeyGenClient(os.environ["HEYGEN_API_KEY"])
        quota_response = client.check_quota()
        logger.info(f"Checked HeyGen quota: {quota_response}")

        for take in takes:
            title = f"Around Town, {episode}, Take {take.id}"
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
            clip_job_path = self.clip_job_path_for(take.id)
            json.dump(clip_job, open(clip_job_path, "w"), indent=4)

            logger.info(f"Started clip job {video_id} with info in {clip_job_path}")

    def wait_and_download_clip_jobs(self):
        client = HeyGenClient(os.environ["HEYGEN_API_KEY"])
        wait_for_jobs = True

        while wait_for_jobs:
            wait_for_jobs = False
            clip_job_paths = sorted(self.clip_jobs_glob())

            for clip_job_path in clip_job_paths:
                clip_job = json.load(open(clip_job_path))
                clip_path = self.clip_path_for(clip_job["clip"])
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
