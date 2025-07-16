import re
import requests
from bs4 import BeautifulSoup
from event import Event
from scraper import Scraper


class VillageOfMamaroneckScraper(Scraper):
    def get_upcoming(self) -> list[Event]:
        r = requests.get("https://www.villageofmamaroneckny.gov/calendar/upcoming")
        html = r.text
        soup = BeautifulSoup(html, features="html.parser")

        items = soup.find_all("div", class_="views-row")

        events = []

        for item in items:
            title = item.find("a").string
            when = item.find("div", class_="views-field-field-date-and-time").div.span.string
            desc = ""
            location = ""

            events.append(Event(
                "Village of Mamaroneck",
                title,
                desc,
                when,
                location
            ))

        return events