import requests


class HeyGenAgent:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = "https://api.heygen.com/v2/"
    
    @property
    def headers(self) -> dict:
        return {
            "accept": "application/json",
            "x-api-key": self.api_key
        }

    def check_quota(self):
        response = requests.get(f"{self.api_url}/user/remaining_quota", headers=self.headers)
        return response.json()