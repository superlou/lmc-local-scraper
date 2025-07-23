import logging
import pandas as pd
from event import Event
import scrapers
import argparse


def run_scraper(scraper) -> list[Event]:
    scraper.info("started")
    events = scraper.get_upcoming()
    scraper.info(f"found {len(events)} events")
    return events


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--ollama", action="store_true")
    parser.add_argument("--filter")
    args = parser.parse_args()

    scraper_classes = scrapers.all

    if not args.ollama:
        scraper_classes = [
            Scraper
            for Scraper in scrapers.all
            if "ollama" not in Scraper.tags
        ]

    if args.filter:
        scraper_classes = [
            Scraper
            for Scraper in scraper_classes
            if args.filter.lower() in Scraper.__name__.lower()
        ]


    events = [event for scraper in scraper_classes for event in run_scraper(scraper())]
    df = pd.DataFrame([x.__dict__ for x in events])
    df.to_csv("events.csv")


if __name__ == "__main__":
    main()
