from datetime import date, timedelta
from pathlib import Path

from fastapi.encoders import isoformat


class GenPathManager:
    def __init__(self, base: str | Path):
        self.base = Path(base)

    def by_date(self, date_: date) -> Path:
        return self.base / date_.isoformat()

    def find_recent(self, today: date, days_back: int) -> list[Path]:
        return [
            p
            for i in range(1, days_back + 1)
            if (p := self.base / (today - timedelta(days=i)).isoformat()).exists()
        ]
