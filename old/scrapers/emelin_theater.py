import re
import requests
from bs4 import BeautifulSoup, Tag
from scraper import Scraper
from event import Event


class EmelinTheaterScraper(Scraper):
    def get_upcoming(self) -> list[Event]:
        events = []

        url = "https://emelin.org/upcoming-shows/"
        html = requests.get(url).text
        soup = BeautifulSoup(html, features="html.parser")

        month = ""
        year = ""

        events_div = soup.find("div", class_="et_pb_section_1")
        if not isinstance(events_div, Tag):
            return []

        for article in events_div.find_all("article", class_="act-post"):
            if not isinstance(article, Tag):
                continue

            title = article.find("h2", class_="entry-title")          

            month_separator = article.find("h2", class_="ecs-events-list-separator-month")
            if month_separator:
                parts = month_separator.get_text().split(",")
                month = parts[0].strip()
                year = parts[1].strip()


            day = article.find("div", class_="callout_date").get_text()
            desc = article.find("p", class_="ecs-excerpt")

            events.append(Event(
                "Emelin Theater",
                title.get_text() if title else "",
                desc.get_text(strip=True) if desc else "",
                f"{month} {day}, {year}",
                "Emelin Theater"
            ))
            

        events = [e for e in events if e is not None]
        return events
