import argparse
import importlib.resources
import tomllib
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from .producer import Producer

load_dotenv()


@logger.catch
def main_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--research", nargs="*")
    parser.add_argument("-w", "--write", nargs="*")
    parser.add_argument("-s", "--storyboard", action="store_true")
    parser.add_argument("-f", "--film", nargs="*", type=int)
    parser.add_argument("-p", "--produce", action="store_true")
    parser.add_argument("--working-dir")
    parser.add_argument("--today")

    args = parser.parse_args()

    today = date.fromisoformat(args.today) if args.today else date.today()

    working_dir = Path(
        args.working_dir if args.working_dir else Path("gen") / today.isoformat()
    )
    working_dir.mkdir(exist_ok=True)
    logger.add(working_dir / "log.txt")
    logger.info(f"Today is {today.strftime('%Y-%m-%d')}")
    logger.info(f"Working in {working_dir}")

    producer = Producer(working_dir, (720, 1280))

    if args.research is not None:
        research_config = importlib.resources.files(__name__) / "assets/research.toml"
        all_targets = tomllib.load(research_config.open("rb"))
        producer.research_events(
            all_targets, today, args.research if len(args.research) > 0 else None
        )

    if args.write is not None:
        try:
            num_events = int(args.write[0])
        except Exception:
            num_events = 4

        producer.write_script(today, num_events)

    if args.storyboard:
        producer.make_storyboard()

    if args.film is not None:
        producer.film_clips(takes_filter=args.film if len(args.film) > 0 else None)

    if args.produce:
        producer.produce_video(today)
