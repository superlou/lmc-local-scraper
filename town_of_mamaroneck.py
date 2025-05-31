import re
import requests
from bs4 import BeautifulSoup
from event import Event
from scraper import Scraper


class TownOfMamaroneckScraper(Scraper):
    def get_upcoming(self) -> list[Event]:
        r = requests.get("https://www.townofmamaroneckny.gov/RSSFeed.aspx?ModID=58&CID=All-calendar.xml")
        html = r.text
        soup = BeautifulSoup(html, features="xml")

        events = []

        for item in soup.channel.find_all("item"):
            source = "Town of Mamaroneck"
            title = item.title.string
            desc = item.description.string

            if desc is not None:
                desc = desc.replace("<strong>", "")
                desc = desc.replace("</strong>", "")
                desc = desc.replace("<b>", "")
                desc = desc.replace("</b>", "")
                desc = desc.replace("<br>", " ")

            dates = item.find("calendarEvent:EventDates").string
            times = item.find("calendarEvent:EventTimes").string
            when = f"{dates} {times}"

            location = item.location

            events.append(Event(
                source,
                title,
                desc,
                when,
                location
            ))

        return events