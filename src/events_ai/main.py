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
    parser.add_argument("-r", "--research", action="store_true")
    parser.add_argument("-w", "--write", action="store_true")
    parser.add_argument("-s", "--storyboard", action="store_true")
    parser.add_argument("-f", "--film", action="store_true")
    parser.add_argument("-p", "--produce", action="store_true")
    parser.add_argument("--working-dir")
    parser.add_argument("--today")
    parser.add_argument("--filter", nargs="+")

    args = parser.parse_args()

    today = date.fromisoformat(args.today) if args.today else date.today()

    working_dir = Path(
        args.working_dir if args.working_dir else Path("gen") / today.isoformat()
    )
    working_dir.mkdir(exist_ok=True)
    logger.add(working_dir / "log.txt")
    logger.info(f"Today is {today.strftime('%Y-%m-%d')}")
    logger.info(f"Working in {working_dir}")

    producer = Producer(working_dir)

    if args.research:
        research_config = importlib.resources.files(__name__) / "research.toml"
        all_targets = tomllib.load(open(research_config, "rb"))
        producer.research_events(all_targets, args.filter, today)

    if args.write:
        producer.write_script(today, 3)

    if args.storyboard:
        producer.make_storyboard()

    if args.film:
        producer.film_clips()

    if args.produce:
        producer.produce_video(today)


if __name__ == "__main__":
    main()
