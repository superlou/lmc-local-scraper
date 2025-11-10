from heygen_client import HeyGenClient


class FilmAgent:
    def __init__(self, api_key):
        self.client = HeyGenClient(api_key)
