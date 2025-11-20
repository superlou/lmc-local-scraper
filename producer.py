import os
from datetime import datetime
from glob import glob
from pathlib import Path

import pandas as pd
from dateutil.relativedelta import relativedelta
from google import genai
from loguru import logger

from agents.event_list_agent import EventListAgent, EventsResult
from agents.flat_event_page_agent import FlatEventPageAgent
from agents.script_writer_agent import ScriptWriterAgent


class Producer:
    def __init__(self, working_dir: Path):
        self.path = working_dir

    def research_events(self, targets, filter: list[str]):
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
            now = datetime.now()
            finish = now + relativedelta(months=1)
            result = agent.run(llm, now, finish)
            df = result_to_df(result)
            df["organization"] = config["organization"]
            logger.info(f"Found {len(df)} events from {target}", tokens=agent.tokens)
            df.to_csv(self.path / f"events_{target}.csv")

        events_files = self.path.glob("events_*.csv")
        df = pd.concat([pd.read_csv(filename) for filename in events_files])

        events_path = self.path / "events.csv"
        df.to_csv(events_path)
        logger.info(f"Collected {len(df)} events into {events_path}")

    def write_script(self, num_events: int):
        llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        df = pd.read_csv(self.path / "events.csv")
        logger.info(f"Loaded {len(df)} events to write script.")
        script_writer = ScriptWriterAgent(df, num_events)
        script = script_writer.run(llm)

        script_path = self.path / "script.json"

        with open(script_path, "w") as script_file:
            script_file.write(script.model_dump_json(indent=4))

        logger.info(f"Script written to {script_path}")


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
