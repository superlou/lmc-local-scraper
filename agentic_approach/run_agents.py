import os

from devtools import debug
from dotenv import load_dotenv
from google import genai
import pandas as pd

from event_list_agent import EventListAgent, EventsResult
from script_writer_agent import ScriptWriterAgent, ScriptResult
from storyboard_agent import StoryboardAgent

load_dotenv()


def result_to_df(result: EventsResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
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
        ]
    )


def main():
    research_events()
    write_script()
    # make_storyboard()


def research_events():
    llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    vom = EventListAgent("https://www.villageofmamaroneckny.gov/calendar/upcoming")
    result = vom.run(llm)
    df = result_to_df(result)
    df.to_csv("gen/vom.csv")

    emelin = EventListAgent("https://emelin.org/upcoming-shows")
    result = emelin.run(llm)
    df = result_to_df(result)
    df.to_csv("gen/emelin.csv")

    made_art = EventListAgent(
        "https://app.getoccasion.com/p/stacks/1229/15216",
        use_selenium=True
    )
    result = made_art.run(llm)
    df = result_to_df(result)
    df.to_csv("gen/made_art.csv")

    df = pd.concat(
        [
            pd.read_csv(filename)
            for filename in ["gen/vom.csv", "gen/emelin.csv", "gen/made_art.csv"]
        ]
    )
    df.to_csv("gen/events.csv")


def write_script():
    llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    df = pd.read_csv("gen/events.csv")
    script_writer = ScriptWriterAgent(df)
    script = script_writer.run(llm)

    with open("gen/script.json", "w") as script_file:
        script_file.write(script.model_dump_json(indent=4))


def make_storyboard():
    llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    script = ScriptResult.model_validate_json(open("gen/script.json").read())
    storyboard = StoryboardAgent(script, "assets/matt.jpg")
    storyboard.run(llm)


if __name__ == "__main__":
    main()
