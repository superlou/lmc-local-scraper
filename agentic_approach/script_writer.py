import os

from dotenv import load_dotenv
from google import genai
import pandas as pd
from pydantic import BaseModel

load_dotenv()

class ScriptResult(BaseModel):
    text: str


class ScriptWriterAgent:
    def __init__(self, csv_files: list[str]):
        self.llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        dfs = [pd.read_csv(filename) for filename in csv_files]
        self.df = pd.concat(dfs)

    def run(self):
        prompt = "Given the following CSV file containing event information, write a news script.\n"
        prompt += "Choose the most 5 most exciting events for the week of 9/8/25.\n"
        prompt += "Write the script in the style of an energetic local personality.\n"
        prompt += "Do not say your name or leave a placeholder for one."
        prompt += "For each event, give the title, the start time, the location, who should attend, and the price (if known).\n"
        prompt += "Before each event, put a [img=<background_placeholder>, music=<music_placeholder>] tag followed by a newline, where placeholder should be a description of an interesting image relevant to the story and a description of fun and appropriate background music. Put the descriptions in quotes.\n"
        prompt += "Put a newline after each event."
        prompt += "\n"
        prompt += self.df.to_csv()

        response = self.llm.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=ScriptResult
            ),
        )

        print(response.parsed.text)


def main():
    #agent = ScriptWriterAgent(["emelin.csv", "vom.csv"])
    agent = ScriptWriterAgent(["events_rob.csv"])
    agent.run()


if __name__ == "__main__":
    main()