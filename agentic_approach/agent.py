import os
import pickle

from devtools import pprint
from dotenv import load_dotenv
from devtools import debug
from google import genai

from event import EventsResult
import simplify_url

load_dotenv()


class EventAgent:
    def __init__(self):
        # self.llm = Gemini(os.environ["GEMINI_API_KEY"])
        self.llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def find_events(self, url) -> EventsResult:
        print(f"Querying {url}")

        page = simplify_url.get(url)

        query = "In the following markdown description of a webpage, extract all events, identifying their name, description, location, and when they occur.\n"
        query += "For all Events, specify dates in YYYY-MM-DD format.\n"
        query += "For all Events, if there is enough information to estimate the target age for the Event, provide a list of one or more of the following: kids, teens, or adults.\n"
        query += "Do not include events that have an unknown or unspecified time or location.\n"
        query += "USE ONLY INFORMATION IN THE WEBPAGE.\n"
        query += "If there are URLs that appear to be links to pages that may contain events, list those in 'event_urls'.\n"
        query += "*Do not include links that are NOT likely to contain more events in 'event_urls'.*\n"
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
        debug(result)
        return

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
    agent.start_from("https://emelin.org/upcoming-shows/")
    # agent.start_from("https://www.villageofmamaroneckny.gov/calendar/upcoming")

    # get_simplified("http://thestemalliance.org", info=True)
    # get_simplified("https://www.westchester.org/events/converge-25/", info=True)


if __name__ == "__main__":
    main()