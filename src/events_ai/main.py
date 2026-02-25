import argparse
import importlib.resources
import os
import tomllib
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

import events_ai.check_setup as check_setup
from events_ai.gen_path_manager import GenPathManager
from events_ai.mailer import Mailer
from events_ai.steps import (
    FilmStep,
    ProduceStep,
    ResearchStep,
    StoryboardStep,
    WriteScriptStep,
)
from events_ai.steps.write_post_step import WritePostStep

load_dotenv()


@logger.catch()
def main_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--skip-check", action="store_true")
    parser.add_argument("-r", "--research", nargs="*")
    parser.add_argument("-w", "--write", nargs="*")
    parser.add_argument("-s", "--storyboard", action="store_true")
    parser.add_argument("-f", "--film", nargs="*", type=int)
    parser.add_argument("-p", "--produce", action="store_true")
    parser.add_argument("-c", "--create-post", action="store_true")
    parser.add_argument("-e", "--email", type=str)
    parser.add_argument("--working-dir")
    parser.add_argument("--today")
    parser.add_argument("--all", action="store_true")

    args = parser.parse_args()

    today = date.fromisoformat(args.today) if args.today else date.today()

    gen_path_manager = GenPathManager("gen")

    if args.working_dir:
        working_dir = Path(args.working_dir)
    else:
        working_dir = gen_path_manager.by_date(today)

    working_dir.mkdir(exist_ok=True)

    logger.add(working_dir / "log.txt")
    logger.info(f"Today is {today.strftime('%Y-%m-%d')}")
    logger.info(f"Working in {working_dir}")

    try:
        generate(working_dir, today, gen_path_manager, args)
        if args.email:
            send_successful_email(args.email, args, today, working_dir)
    except Exception as e:
        if args.email:
            send_failure_email(args.email, args, today, working_dir)
        raise (e)


def generate(working_dir: Path, today: date, gen_path_manager: GenPathManager, args):
    if not args.skip_check:
        check_setup.check()

    ASSETS_DIR = importlib.resources.files(__name__) / "assets"
    events_path = working_dir / "events.csv"
    research_tokens_path = working_dir / "research_tokens.csv"
    script_path = working_dir / "script.json"
    storyboard_path = working_dir / "storyboard.json"
    clip_path = working_dir / "clip.mp4"
    video_path = working_dir / "video.mp4"
    post_path = working_dir / "post.txt"

    # Research
    research = ResearchStep(events_path, research_tokens_path)
    do_research = (args.research is not None) or (args.all and not research.done)
    research_filter = args.research if len(args.research or []) > 0 else None

    if do_research:
        research_config = importlib.resources.files(__name__) / "assets/research.toml"
        all_targets = tomllib.load(research_config.open("rb"))
        research.run(all_targets, today, research_filter)

    # Write
    write_script = WriteScriptStep(script_path, events_path)
    do_script = (args.write is not None) or (args.all and not write_script.done)
    if do_script:
        try:
            num_events = int(args.write[0])
        except Exception:
            num_events = 4

        write_script.run(today, num_events, gen_path_manager.find_recent(today, 3))

    # Storyboard
    storyboard = StoryboardStep(storyboard_path, script_path, ASSETS_DIR)
    do_storyboard = args.storyboard or (args.all and not storyboard.done)
    if do_storyboard:
        storyboard.run(720, 1280)

    # Film
    film = FilmStep(clip_path, storyboard_path, ASSETS_DIR)
    do_film = (args.film is not None) or (args.all and not film.done)
    film_filter = args.film if len(args.film or []) > 0 else None
    if do_film:
        film.run(takes_filter=film_filter, episode=str(today))

    # Produce
    produce = ProduceStep(video_path, storyboard_path, clip_path, ASSETS_DIR)
    do_produce = args.produce or (args.all and not produce.done)
    if do_produce:
        produce.run(today)

    # Create post
    write_post = WritePostStep(post_path, script_path)
    do_post = args.create_post or (args.all and not write_post.done)
    if do_post:
        write_post.run(today)


def send_successful_email(destination: str, args, today: date, working_dir: Path):
    mailer = Mailer("gen-ai-bot@lmc-tv.org", os.environ["GMAIL_USER_APP_PASSWORD"])
    mailer.subject = f"AI events bot finished - {working_dir}"
    mailer.body = "AI events bot finished successfully."
    mailer.body += f"\nargs = {args}"
    mailer.attach(open(working_dir / "log.txt"), f"log_{today}.txt")
    mailer.attach(open(working_dir / "events.csv"), f"events_{today}.csv")
    mailer.attach(open(working_dir / "script.json"), f"script_{today}.json")
    mailer.attach(open(working_dir / "storyboard.json"), f"storyboard_{today}.json")
    mailer.attach(open(working_dir / "video.mp4", "rb"), f"video_{today}.mp4")
    mailer.attach(open(working_dir / "post.txt"), f"post_{today}.txt")
    mailer.send(destination)


def try_to_attach(mailer: Mailer, file_path: Path, filename: str, mode: str = "r"):
    try:
        mailer.attach(open(file_path, mode), filename)
    except FileNotFoundError:
        logger.warning(f"Failed to find file to attach as {filename}")


def send_failure_email(destination: str, args, today: date, working_dir: Path):
    mailer = Mailer("gen-ai-bot@lmc-tv.org", os.environ["GMAIL_USER_APP_PASSWORD"])
    mailer.subject = f"AI events bot failed! - {working_dir}"
    mailer.body = "AI events bot failed to generate."
    mailer.body += f"\nargs = {args}"
    try_to_attach(mailer, working_dir / "log.txt", f"log_{today}.txt")
    try_to_attach(mailer, working_dir / "events.csv", f"events_{today}.csv")
    try_to_attach(mailer, working_dir / "script.json", f"script_{today}.json")
    try_to_attach(mailer, working_dir / "storyboard.json", f"storyboard_{today}.json")
    try_to_attach(mailer, working_dir / "video.mp4", f"video_{today}.mp4", "rb")
    try_to_attach(mailer, working_dir / "post.txt", f"post_{today}.txt")
    mailer.send(destination)
