import re
import requests
from bs4 import BeautifulSoup
from scraper import Scraper
from event import Event


class LarchmontPublicLibraryScraper(Scraper):
    def get_upcoming(self) -> list[Event]:
        r = requests.get("https://larchmont.librarycalendar.com/events/list")
        html = r.text
        soup = BeautifulSoup(html, features="html.parser")

        upcoming = soup.find("section", class_="calendar--list")
        articles = upcoming.find_all("article", class_="event-card")

        events = []

        for article in articles:
            title = article.find("h2").a.string.strip()

            date_div = article.find("div", class_="lc-list-event-date")
            when_text = date_div.div.string.strip() if date_div else ""
            when = re.sub(" +", " ", when_text).replace("\n", "")

            location_div = article.find("div", class_="lc-event-info__item--categories")
            location = location_div.string.strip() if location_div else ""

            desc_div = article.find("div", class_="lc-list-event-description")
            desc = desc_div.p.string.strip() if desc_div and desc_div.p.string else ""

            events.append(Event("Larchmont Public Library", title, desc, when, location))

        return events