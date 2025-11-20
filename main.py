import argparse
import json
import os
import time
import tomllib
from datetime import datetime
from glob import glob
from pathlib import Path

import pandas as pd
import requests
from devtools import debug
from dotenv import load_dotenv
from fpdf import FPDF
from google import genai
from loguru import logger
from moviepy import VideoFileClip, concatenate_videoclips
from pydantic import ValidationError

from agents.film_agent import FilmAgent
from agents.heygen_client import HeyGenClient
from agents.script_writer_agent import ScriptResult, ScriptWriterAgent
from agents.storyboard_agent import StoryboardAgent, StoryboardResult
from producer import Producer

load_dotenv()


@logger.catch
def main():
    logger.add("gen/log.txt")

    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--research", action="store_true")
    parser.add_argument("-w", "--write", action="store_true")
    parser.add_argument("-s", "--storyboard", action="store_true")
    parser.add_argument("-f", "--film", action="store_true")
    parser.add_argument("-p", "--produce", action="store_true")
    parser.add_argument(
        "--working-dir", default="gen/" + datetime.now().strftime("%Y-%m-%d")
    )
    parser.add_argument("--filter", nargs="+")

    args = parser.parse_args()

    working_dir = Path(args.working_dir)
    working_dir.mkdir(exist_ok=True)
    logger.add(working_dir / "log.txt")
    logger.info(f"Working in {working_dir}")

    producer = Producer(working_dir)

    if args.research:
        all_targets = tomllib.load(open("research.toml", "rb"))
        producer.research_events(all_targets, args.filter)

    if args.write:
        producer.write_script()

    # if args.storyboard:
    #     make_storyboard()

    # if args.film:
    #     film_clips()

    # if args.produce:
    #     produce_video()


def make_storyboard():
    llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    script = ScriptResult.model_validate_json(open("gen/script.json").read())
    storyboard = StoryboardAgent(script, "assets/studio_background.png")
    result = storyboard.run(llm)

    with open("gen/storyboard.json", "w") as script_file:
        script_file.write(result.model_dump_json(indent=4))

    storyboard_to_pdf(
        StoryboardResult.model_validate_json(open("gen/storyboard.json").read())
    )


def storyboard_to_pdf(storyboard: StoryboardResult):
    debug(storyboard)
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("NotoSans", "", "assets/NotoSans-Regular.ttf")
    pdf.set_font("NotoSans", size=12)

    for take in storyboard.takes:
        pdf.image(take.frame, h=40)
        pdf.multi_cell(0, 10, text=take.text, new_x="LMARGIN", new_y="NEXT")

    pdf.output("gen/storyboard.pdf")


def film_clips():
    client = HeyGenClient(os.environ["HEYGEN_API_KEY"])
    quota_response = client.check_quota()
    logger.info("Checked HeyGen quota", response=quota_response)

    storyboard = StoryboardResult.model_validate_json(
        open("gen/storyboard.json").read()
    )

    for take in storyboard.takes:
        agent = FilmAgent(
            os.environ["HEYGEN_API_KEY"],
            take.text,
            take.frame,
            "gen/intro.mp4",
        )
        video_id = agent.run()

        video_process = {
            "clip": take.id,
            "processor": "HeyGen Avatar V2",
            "video_id": video_id,
        }
        json.dump(video_process, open(f"gen/clip_{take.id}.txt", "w"), indent=4)

    wait_for_generation = True

    # todo Get smarter about checking videos that already completed.
    # Download them as soon as they're ready.
    while wait_for_generation:
        time.sleep(10)
        wait_for_generation = False

        clip_files = sorted(glob("gen/clip_*.txt"))

        for video_process_file in clip_files:
            video_process = json.load(open(video_process_file))
            video_id = video_process["video_id"]

            try:
                response = client.get_video_status(video_id)
                # response = VideoStatusResponse(code=100, data={"status": "completed"})
                status = response.data["status"]
                video_url = response.data["video_url"]
                print(f"Clip {video_process['clip']}: {status}, {video_url}")
                if status != "completed":
                    wait_for_generation = True
            except ValidationError:
                pass

        print()

    # Download all video clips
    clip_files = sorted(glob("gen/clip_*.txt"))

    for video_process_file in clip_files:
        video_process = json.load(open(video_process_file))
        video_id = video_process["video_id"]
        clip = video_process["clip"]

        response = client.get_video_status(video_id)
        status = response.data["status"]
        video_url = response.data["video_url"]

        try:
            print(f"Downloading clip {clip}...")
            response = requests.get(video_url, stream=True)
            with open(f"gen/clip_{clip}.mp4", "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except requests.exceptions.RequestException as e:
            print("Error downloading file.")
        except IOError as e:
            print("Error saving file.")


def produce_video():
    clip_files = sorted(glob("gen/clip_*.mp4"))
    clips = [VideoFileClip(clip_file) for clip_file in clip_files]
    video = concatenate_videoclips(clips)
    print("Writing final video...")
    video.write_videofile("gen/video.mp4")
    print("done.")


if __name__ == "__main__":
    main()
