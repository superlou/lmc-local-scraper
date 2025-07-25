import re
import requests
from bs4 import BeautifulSoup, Tag
from scraper import Scraper
from event import Event


class SheldrakeCenter(Scraper):
    def get_upcoming(self) -> list[Event]:
        events = []

        url = "https://sheldrakecenter.org/upcoming-events/"
        html = requests.get(url).text
        soup = BeautifulSoup(html, features="html.parser")

        posts = soup.find_all("article", class_="act-post")
        for post in posts:
            if not isinstance(post, Tag):
                continue
        
            title = post.find("h2", class_="title2")

            date = post.find("span", class_="decm_date")
            time = post.find("span", class_="decm_time")
            when = date.get_text() if date else ""
            when += ", " + time.get_text() if time else ""

            location = post.find("span", class_="decm_location")
            
            events.append(Event(
                source="Sheldrake Environmental Center",
                title=title.get_text() if title else "",
                desc=title.get_text() if title else "",
                when=when,
                location=location.get_text() if location else ""
            ))

        return events
