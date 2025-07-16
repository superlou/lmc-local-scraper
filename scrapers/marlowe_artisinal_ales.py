import requests
from bs4 import BeautifulSoup
from event import Event
from ollama import chat, ChatResponse
from pydantic import BaseModel
from scraper import Scraper


class EventList(BaseModel):
    events: list[Event]


class MarloweArtisinalAlesScraper(Scraper):
    tags = ["ollama"]

    def get_upcoming(self):
        r = requests.get("https://www.marloweales.com/hghg")
        soup = BeautifulSoup(r.text, features="html.parser")

        content = soup.find("div", class_="content").get_text().strip()

        prompt = ("Extract events from the following HTML that begins after <<<HTML>>>\n"
                + "List the events in JSON with the following attributes: source, title, desc (description), when (date and time), location\n"
                + "The source is always Marlowe Artisanal Ales"
                + "The location is always Marlowe Artisanal Ales")

        response = chat(model="gemma3", messages=[
            {
                "role": "user",
                "content": prompt + "\n<<<START>>>\n" + content
            },
        ], format=EventList.model_json_schema())

        # print(response.message.content)
        event_list = EventList.model_validate_json(response.message.content)
        
        return [Event(e.source, e.title, e.desc, e.when, e.location) for e in event_list.events]