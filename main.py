import logging
import pandas as pd
from larchmont_public_library import LarchmontPublicLibraryScraper
from town_of_mamaroneck import TownOfMamaroneckScraper
from village_of_mamaroneck import VillageOfMamaroneckScraper
from marlowe_artisinal_ales import MarloweArtisinalAlesScraper
from event import Event


def run_scraper(scraper) -> list[Event]:
    scraper.info("started")
    events = scraper.get_upcoming()
    scraper.info(f"found {len(events)} events")
    return events


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    scrapers = [
        LarchmontPublicLibraryScraper(),
        TownOfMamaroneckScraper(),
        VillageOfMamaroneckScraper(),
        MarloweArtisinalAlesScraper(),
    ]

    events = [event for scraper in scrapers for event in run_scraper(scraper)]

    df = pd.DataFrame([x.__dict__ for x in events])
    df.to_csv("events.csv")


if __name__ == "__main__":
    main()
