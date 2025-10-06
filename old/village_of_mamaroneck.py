import os
from urllib.parse import urlparse

from devtools import debug
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

import simplify_url

load_dotenv()


class Event(BaseModel):
    title: str
    link: str | None
    description: str
    when: str
    location: str
    price: str | None
    target_age: list[str]


class EventsResult(BaseModel):
    events: list[Event]
    # other_urls: list[str]



class VillageOfMamaroneckAgent:
    def __init__(self):
        self.start_url = "https://www.villageofmamaroneckny.gov/calendar/upcoming"
        parsed_url = urlparse(self.start_url)
        self.url_base = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def run(self) -> EventsResult:
        start_page = simplify_url.get(self.start_url)

        prompt = "In the following markdown description of a webpage, extract all events, identifying their name, description, location, and when they occur.\n"
        prompt += "For all Events, specify dates in YYYY-MM-DD format.\n"
        prompt += "For all Events, if there is enough information to estimate the target age for the Event, provide a list of one or more of the following: kids, teens, or adults.\n"
        prompt += "Do not include events that have an unknown or unspecified time or location.\n"
        prompt += "USE ONLY INFORMATION IN THE WEBPAGE.\n"
        prompt += "If there are URLs that appear to be links to pages that may contain events, list those in 'event_urls'.\n"
        prompt += "*Do not include links that are NOT likely to contain more events in 'event_urls'.*\n"
        prompt += "\n"
        prompt += start_page

        response = self.llm.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=EventsResult
            ),
        )
        result:EventsResult = response.parsed

        for i, event in enumerate(result.events):
            if event.link is None:
                continue

            print(f"[{i + 1}/{len(result.events)}] Following {event.link}")

            if event.link[0] == "/":
                event.link = self.url_base + event.link

            event_page = simplify_url.get(event.link)
            result = self.update_with_details(event_page, result)
            debug(result)

        return result
    
    def update_with_details(self, page:str, result:EventsResult) -> EventsResult:
        prompt = "The events we know about are in the following JSON structure:\n"
        prompt += result.model_dump_json()
        prompt += "\n"
        prompt += "Given these events, use the following information to add details to the matching event.\n"
        prompt += "\n"
        prompt += page

        response = self.llm.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=EventsResult
            ),
        )

        new_result:EventsResult = response.parsed
        return new_result


if __name__ == "__main__":
    agent = VillageOfMamaroneckAgent()
    result = agent.run()
    debug(result)

    from pandas import DataFrame
    df = DataFrame([
        {
            "event": event.title,
            "link": event.link,
            "description": event.description,
            "when": event.when,
            "location": event.location,
            "price": event.price,
            "target_age": ", ".join(event.target_age),
        }
        for event in result.events
    ])
    print(df)
    df.to_csv("vom.csv")
