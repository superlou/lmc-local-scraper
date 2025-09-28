import argparse
import os
import tomllib

from devtools import debug
from dotenv import load_dotenv
from fpdf import FPDF
from google import genai
import structlog
import pandas as pd

from event_list_agent import EventListAgent, EventsResult
from flat_event_page_agent import FlatEventPageAgent
from script_writer_agent import ScriptWriterAgent, ScriptResult
from storyboard_agent import StoryboardAgent, StoryboardResult

load_dotenv()
log = structlog.get_logger()


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
    parser.add_argument("--filter", nargs="+")

    args = parser.parse_args()

    if args.research:
        research_events(filter=args.filter)

    if args.write:
        write_script()

    if args.storyboard:
        make_storyboard()


def research_events(filter: list[str]):
    llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    all_targets = tomllib.load(open("agentic_approach/research.toml", "rb"))
    log.info(f"Found {len(all_targets)} research targets")

    if filter and len(filter) > 0:
        targets = {
            target: config for target, config in all_targets.items() if target in filter
        }
    else:
        targets = all_targets

    log.info(f"Running {len(targets)} research targets")

    for target, config in targets.items():
        if config["agent"] == "EventListAgent":
            agent = EventListAgent(
                config["url"], use_selenium=config.get("use_selenium", False)
            )
        elif config["agent"] == "FlatEventPageAgent":
            agent = FlatEventPageAgent(config["url"])
        else:
            log.warning(f"Target {target} specified unknown agent {config['agent']}")
            continue

        log.info(f"Researching {target}")
        result = agent.run(llm)
        df = result_to_df(result)
        df["organization"] = "Village of Mamaroneck"
        log.info(f"Found {len(df)} events from {target}")
        df.to_csv(f"gen/{target}.csv")

    filenames = [f"gen/{target}.csv" for target in all_targets.keys()]
    df = pd.concat([pd.read_csv(filename) for filename in filenames])

    events_path = "gen/events.csv"
    df.to_csv(events_path)
    log.info(f"Collected {len(df)} events into {events_path}")


def write_script():
    llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    df = pd.read_csv("gen/events.csv")
    log.info(f"Loaded {len(df)} events to write script.")
    script_writer = ScriptWriterAgent(df)
    script = script_writer.run(llm)

    script_path = "gen/script.json"

    with open(script_path, "w") as script_file:
        script_file.write(script.model_dump_json(indent=4))
    
    log.info(f"Script written to {script_path}")


def make_storyboard():
    llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    script = ScriptResult.model_validate_json(open("gen/script.json").read())
    storyboard = StoryboardAgent(script, "assets/matt.jpg")
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
    pdf.set_font("helvetica", size=12)

    for take in storyboard.takes:
        pdf.image(take.frame, h=40)
        pdf.multi_cell(0, 10, text=take.text, new_x="LMARGIN", new_y="NEXT")

    pdf.output("gen/storyboard.pdf")


if __name__ == "__main__":
    main()
