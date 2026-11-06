import argparse
import importlib.resources
import os
import tomllib
import traceback
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

import events_ai.check_setup as check_setup
from events_ai.gen_path_manager import GenPathManager
from events_ai.overview import Overview, StepStatus, send_overview_email
from events_ai.steps import (
    FilmStep,
    ProduceStep,
    ResearchStep,
    StoryboardStep,
    WriteScriptStep,
)
from events_ai.steps.site_db_step import SiteDBStep
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
    parser.add_argument("-t", "--site-db", action="store_true")
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

    token_usage_path = working_dir / "gemini_token_usage.jsonl"
    token_usage_path.unlink(missing_ok=True)
    os.environ["LMC_RUN_TOKEN_USAGE_PATH"] = str(token_usage_path)

    overview = Overview(working_dir=working_dir, today=today, args=args)

    try:
        generate(working_dir, today, gen_path_manager, args, overview)
    except Exception as e:
        overview.exception = e
        overview.traceback = traceback.format_exc()
        raise (e)
    finally:
        overview.finished_at = datetime.now()
        if args.email:
            send_overview_email(args.email, args, today, working_dir, overview)


def generate(
    working_dir: Path,
    today: date,
    gen_path_manager: GenPathManager,
    args,
    overview: Overview,
):
    if not args.skip_check:
        overview.do_check = StepStatus.INCOMPLETE
        check_setup.check()
        overview.do_check = StepStatus.DONE

    ASSETS_DIR = importlib.resources.files(__name__) / "assets"
    events_path = working_dir / "events.csv"
    research_tokens_path = working_dir / "research_tokens.csv"
    script_path = working_dir / "script.json"
    storyboard_path = working_dir / "storyboard.json"
    clip_path = working_dir / "clip.mp4"
    video_path = working_dir / "video.mp4"
    post_path = working_dir / "post.txt"
    site_db_path = working_dir / "site_db.json"

    # Research
    research = ResearchStep(events_path, research_tokens_path)
    do_research = (args.research is not None) or (args.all and not research.done)
    research_filter = args.research if len(args.research or []) > 0 else None

    if do_research:
        overview.do_research = StepStatus.INCOMPLETE
        research_config = importlib.resources.files(__name__) / "assets/research.toml"
        all_targets = tomllib.load(research_config.open("rb"))
        research.run(all_targets, today, research_filter)
        overview.do_research = StepStatus.DONE

    # Write
    write_script = WriteScriptStep(script_path, events_path)
    do_script = (args.write is not None) or (args.all and not write_script.done)
    if do_script:
        overview.do_script = StepStatus.INCOMPLETE
        try:
            num_events = int(args.write[0])
        except Exception:
            num_events = 4

        write_script.run(today, num_events, gen_path_manager.find_recent(today, 5))
        overview.do_script = StepStatus.DONE

    # Storyboard
    storyboard = StoryboardStep(storyboard_path, script_path, ASSETS_DIR)
    do_storyboard = args.storyboard or (args.all and not storyboard.done)
    if do_storyboard:
        overview.do_storyboard = StepStatus.INCOMPLETE
        storyboard.run(720, 1280)
        overview.do_storyboard = StepStatus.DONE

    # Film
    film = FilmStep(clip_path, storyboard_path, ASSETS_DIR)
    do_film = (args.film is not None) or (args.all and not film.done)
    film_filter = args.film if len(args.film or []) > 0 else None
    if do_film:
        overview.do_film = StepStatus.INCOMPLETE
        film.run(takes_filter=film_filter, episode=str(today))
        overview.do_film = StepStatus.DONE

    # Produce
    produce = ProduceStep(video_path, storyboard_path, clip_path, ASSETS_DIR)
    do_produce = args.produce or (args.all and not produce.done)
    if do_produce:
        overview.do_produce = StepStatus.INCOMPLETE
        produce.run(today)
        overview.do_produce = StepStatus.DONE

    # Create post
    write_post = WritePostStep(post_path, script_path)
    do_post = args.create_post or (args.all and not write_post.done)
    if do_post:
        overview.do_create_post = StepStatus.INCOMPLETE
        write_post.run(today)
        overview.do_create_post = StepStatus.DONE

    # Build Site DB
    site_db = SiteDBStep(events_path, site_db_path)
    do_site_db = args.site_db or (args.all and not site_db.done)
    if do_site_db:
        overview.do_site_db = StepStatus.INCOMPLETE
        (working_dir / "site_db_run_report.json").unlink(missing_ok=True)
        site_db.run(today, 3, gen_path_manager.find_recent(today, 5))
        overview.do_site_db = StepStatus.DONE
