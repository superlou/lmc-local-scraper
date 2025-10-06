# This was an experiment before I switched to the genai package
import requests


GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


class Gemini:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": api_key,
        }


    def ask(self, query:str):
        response = requests.post(GEMINI_API, json={
            "contents": [
                {
                    "parts": [
                        {"text": query}
                    ]
                }
            ]
        }, headers=self.headers)
        return response.json()