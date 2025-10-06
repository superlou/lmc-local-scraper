import re
import requests
from bs4 import BeautifulSoup
import icalendar
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

    # The ical for the VOM goes back to 2019 and is very slow to fetch.
    # def get_upcoming(self) -> list[Event]:
    #     ical_addr = "http://www.villageofmamaroneckny.gov/calendar/ical/export.ics"
    #     r = requests.get(
    #         ical_addr,
    #         headers={
    #             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3835.0 Safari/537.36",
    #             "Accept": "*/*",
    #         },
    #     )
    #     print(r.text)
    #     print(r)

    #     calendar = icalendar.Calendar.from_ical(r.text)
    #     for event in calendar.events:
    #         print(event.get("SUMMARY"))
