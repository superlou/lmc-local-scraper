import logging
import pandas as pd
from event import Event
import scrapers


def run_scraper(scraper) -> list[Event]:
    scraper.info("started")
    events = scraper.get_upcoming()
    scraper.info(f"found {len(events)} events")
    return events


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    active_scrapers = [
        Scraper()
        for Scraper in scrapers.all
        if "ollama" not in Scraper.tags
    ]
    events = [event for scraper in active_scrapers for event in run_scraper(scraper)]
    df = pd.DataFrame([x.__dict__ for x in events])
    df.to_csv("events.csv")


if __name__ == "__main__":
    main()
