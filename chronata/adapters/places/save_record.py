import json
from datetime import datetime
from pathlib import Path


class SaveRecord:
    def __init__(self, path: Path):
        self.path = path

    def last(self, place_id: str) -> dict:
        return self._saves().get(place_id, {})

    def remember(self, place_id: str, when: datetime, error: str | None) -> None:
        self.note(place_id, attempted=when.isoformat(), error=error, **({} if error else {"saved": when.isoformat()}))

    def note(self, place_id: str, **fields) -> None:
        saves = self._saves()
        saves[place_id] = {**saves.get(place_id, {}), **fields}
        self.path.write_text(json.dumps(saves, indent=2) + "\n", encoding="utf-8")

    def _saves(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
