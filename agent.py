import os
import pickle

from bs4 import BeautifulSoup
from devtools import pprint
from dotenv import load_dotenv
from markdownify import markdownify
from pydantic import BaseModel
import requests

from google import genai

load_dotenv()

class Event(BaseModel):
    title: str
    description: str
    when: str
    location: str


class EventsResult(BaseModel):
    events: list[Event]
    other_urls: list[str]


def get_simplified(url: str, info=False) -> str:
    if info:
        print(f"Getting {url}...", end="", flush=True)

    response = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
    })
    html = response.text

    soup = BeautifulSoup(html, "html.parser")
    script_tags = soup.find_all("script")
    for script in script_tags:
        script.decompose()
    
    simplified = soup.body.decode_contents()
    simplified = markdownify(simplified, strip=["img"])

    if info:
        print(f"{len(html):,} -> {len(simplified):,} characters.")

    return simplified
    


class EventAgent:
    def __init__(self):
        # self.llm = Gemini(os.environ["GEMINI_API_KEY"])
        self.llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def find_events(self, url) -> EventsResult:
        print(f"Querying {url}")

        page = get_simplified(url)

        query = "In the following markdown description of a webpage, extract all events, identifying their name, description, location, and when they occur.\n"
        query = "Do not include events that have an unknown or unspecified time or location.\n",
        query = "USE ONLY INFORMATION IN THE WEBPAGE.\n"
        query += "If there are URLs that appear to be links to pages that may contain events, list those urls. Do not include links that are NOT likely to contain more events.\n"
        query += "\n"
        query += page

        response = self.llm.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=query,
            config=genai.types.GenerateContentConfig(
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=EventsResult
            ),
        )
        result:EventsResult = response.parsed
        return result

    def start_from(self, start_url):
        events = []

        result = self.find_events(start_url)
        events += result.events

        for url in result.other_urls:
            if url.startswith("mailto:"):
                continue

            if url[0] == "/":
                url = start_url + url

            events += self.find_events(url).events
            pickle.dump(events, open("events.pickle", "wb"))

        pickle.dump(events, open("events.pickle", "wb"))
        pprint(events)



def main():
    agent = EventAgent()
    # agent.start_from("http://thestemalliance.org")
    agent.start_from("https://emelin.org/")

    # get_simplified("http://thestemalliance.org", info=True)
    # get_simplified("https://www.westchester.org/events/converge-25/", info=True)


if __name__ == "__main__":
    main()