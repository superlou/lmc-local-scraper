import os
from datetime import date
from pathlib import Path
from typing import Generator

import pandas as pd
from dateutil.relativedelta import relativedelta
from google import genai
from loguru import logger

from events_ai.agents.research_agent_factory import ResearchAgentFactory
from events_ai.steps.pipeline_step import PipelineStep

from ..agents.gemini_event_research_agent import EventsResult


class ResearchStep(PipelineStep):
    def __init__(self, events_path: Path, research_tokens_path: Path):
        self.events_path = events_path
        self.research_tokens_path = research_tokens_path
        self.token_tracker = ResearchTokenTracker()

    @property
    def done(self) -> bool:
        return self.events_path.exists()

    def events_path_for(self, org: str) -> Path:
        filename = f"{self.events_path.stem}_{org}{self.events_path.suffix}"
        return self.events_path.parent / filename

    def events_glob(self) -> Generator[Path, None, None]:
        return self.events_path.parent.glob(self.events_path_for("*").name)

    def run(self, targets, today: date, filter: list[str] | None = None):
        llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        finish = today + relativedelta(months=1)

        all_targets = targets
        logger.info(f"Found {len(all_targets)} research targets")

        if filter is not None and len(filter) > 0:
            targets = {
                target: config
                for target, config in all_targets.items()
                if target in filter
            }
        else:
            targets = all_targets

        logger.info(f"Running {len(targets)} research targets")

        for target, config in targets.items():
            try:
                agent = ResearchAgentFactory.build(llm, today, finish, **config)
            except ValueError as exc:
                logger.warning(f"Target {target} skipped: {exc}")
                continue

            try:
                logger.info(f"Researching {target}")
                result = agent.run()
                df = result_to_df(result)
                df["organization"] = config["organization"]
                logger.info(
                    f"Found {len(df)} events from {target}. Tokens used: {agent.tokens}"
                )
                self.token_tracker.record(
                    target, agent.tokens.prompt, agent.tokens.candidates
                )
                df.to_csv(self.events_path_for(target), index_label="id")
            except Exception as err:
                logger.warning(f"Exception researching {target}: {err}")

        events_files = self.events_glob()
        df = pd.concat(
            [pd.read_csv(filename, index_col="id") for filename in events_files],
            ignore_index=True,
        )

        df.to_csv(self.events_path, index_label="id")
        logger.info(f"Collected {len(df)} events into {self.events_path}")
        self.token_tracker.save(self.research_tokens_path)


class ResearchTokenTracker:
    def __init__(self):
        self.ledger = []

    def record(self, name: str, prompt: int, candidate: int):
        self.ledger.append(
            {"name": name, "prompt_tokens": prompt, "candidate_tokens": candidate}
        )

    def save(self, path: Path):
        df = pd.DataFrame(self.ledger)
        df.to_csv(path, index=False)


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
