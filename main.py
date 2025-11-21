import argparse
import tomllib
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

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
        producer.write_script(3)

    if args.storyboard:
        producer.make_storyboard()

    if args.film:
        producer.film_clips()

    if args.produce:
        producer.produce_video()


if __name__ == "__main__":
    main()
