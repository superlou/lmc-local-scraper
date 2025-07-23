import re
import requests
from bs4 import BeautifulSoup
from scraper import Scraper
from event import Event


class EmelinTheaterScraper(Scraper):
    def get_upcoming(self) -> list[Event]:
        events = []

        url = "https://emelin.org/upcoming-shows/"
        html = requests.get(url).text
        soup = BeautifulSoup(html, features="html.parser")

        last_separator = ""

        events_div = soup.find("div", class_="et_pb_section_1")

        for article in events_div.find_all("article", class_="act-post"):
            title = article.find("h2", class_="entry-title")          
            name = title.a.string

            month_separator = article.find("h2", class_="ecs-events-list-separator-month")
            if month_separator:
                last_separator = month_separator.string

            day = article.find("div", class_="callout_date").string
            
            if excerpt := article.find("p", class_="ecs-excerpt"):
                desc = excerpt.string.strip()
            else:
                desc = ""

            events.append(Event(
                "Emelin Theater",
                name,
                desc,
                f"{day}, {last_separator}",
                "Emelin Theater"
            ))
            

        events = [e for e in events if e is not None]
        return events
