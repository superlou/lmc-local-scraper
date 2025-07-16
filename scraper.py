import logging
from event import Event


class Scraper:
    tags = []

    def get_upcoming(self) -> list[Event]:
        raise NotImplementedError()
    
    def info(self, text) -> None:
        logging.info(f"{self.__class__.__name__} {text}")
