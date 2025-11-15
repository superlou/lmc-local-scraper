import argparse
import os
import tomllib
from datetime import datetime

import pandas as pd
import structlog
from dateutil.relativedelta import relativedelta
from devtools import debug
from dotenv import load_dotenv
from fpdf import FPDF
from google import genai

from agents.event_list_agent import EventListAgent, EventsResult
from agents.film_agent import FilmAgent
from agents.flat_event_page_agent import FlatEventPageAgent
from agents.script_writer_agent import ScriptResult, ScriptWriterAgent
from agents.storyboard_agent import StoryboardAgent, StoryboardResult

load_dotenv()
logger = structlog.get_logger()


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--research", action="store_true")
    parser.add_argument("-w", "--write", action="store_true")
    parser.add_argument("-s", "--storyboard", action="store_true")
    parser.add_argument("-f", "--film", action="store_true")
    parser.add_argument("--filter", nargs="+")

    args = parser.parse_args()

    if args.research:
        research_events(filter=args.filter)

    if args.write:
        write_script()

    if args.storyboard:
        make_storyboard()

    if args.film:
        film_segments()


def research_events(filter: list[str]):
    llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    all_targets = tomllib.load(open("research.toml", "rb"))
    logger.info(f"Found {len(all_targets)} research targets")

    if filter and len(filter) > 0:
        targets = {
            target: config for target, config in all_targets.items() if target in filter
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
            logger.warning(f"Target {target} specified unknown agent {config['agent']}")
            continue

        logger.info(f"Researching {target}")
        now = datetime.now()
        finish = now + relativedelta(months=1)
        result = agent.run(llm, now, finish)
        df = result_to_df(result)
        df["organization"] = config["organization"]
        log = logger.bind(tokens=agent.tokens)
        log.info(f"Found {len(df)} events from {target}")
        df.to_csv(f"gen/{target}.csv")

    filenames = [f"gen/{target}.csv" for target in all_targets.keys()]
    df = pd.concat([pd.read_csv(filename) for filename in filenames])

    events_path = "gen/events.csv"
    df.to_csv(events_path)
    logger.info(f"Collected {len(df)} events into {events_path}")


def write_script():
    llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    df = pd.read_csv("gen/events.csv")
    logger.info(f"Loaded {len(df)} events to write script.")
    script_writer = ScriptWriterAgent(df)
    script = script_writer.run(llm)

    script_path = "gen/script.json"

    with open(script_path, "w") as script_file:
        script_file.write(script.model_dump_json(indent=4))

    logger.info(f"Script written to {script_path}")


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


def film_segments():
    storyboard = StoryboardResult.model_validate_json(
        open("gen/storyboard.json").read()
    )

    heygen = FilmAgent(
        os.environ["HEYGEN_API_KEY"],
        storyboard.takes[0].text,
        storyboard.takes[0].frame,
        "gen/intro.mp4",
    )
    # quota_response = heygen.check_quota()
    # log = logger.bind(response=quota_response)
    # log.info("Checked HeyGen quota")
    heygen.run()


if __name__ == "__main__":
    main()
