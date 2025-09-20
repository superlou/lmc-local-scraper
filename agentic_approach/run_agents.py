import os

from dotenv import load_dotenv
from google import genai
import pandas as pd

from event_list_agent import EventListAgent, EventsResult
from script_writer_agent import ScriptWriterAgent


def result_to_df(result: EventsResult) -> pd.DataFrame:
    return pd.DataFrame([
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


def main():
    load_dotenv()
    llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    vom = EventListAgent("https://www.villageofmamaroneckny.gov/calendar/upcoming")
    result = vom.run(llm, 0)
    df = result_to_df(result)
    df.to_csv("vom.csv")

    emelin = EventListAgent("https://emelin.org/upcoming-shows")
    result = emelin.run(llm, 2)
    df = result_to_df(result)
    df.to_csv("emelin.csv")

    made_art = EventListAgent("https://app.getoccasion.com/p/stacks/1229/15216")
    result = made_art.run(llm, use_selenium=True)
    df = result_to_df(result)
    df.to_csv("made_art.csv")

    script_writer = ScriptWriterAgent()
    df = pd.concat([
        pd.read_csv(filename)
        for filename in ["vom.csv", "emelin.csv", "made_art.csv"]
    ])
    script = script_writer.run(llm, df)
    print(script)
    with open("script.txt", "w") as script_file:
        script_file.write(script)


if __name__ == "__main__":
    main()