import json
from datetime import datetime
from pathlib import Path

from chronata.adapters.storage.owner_only_file import write_owner_only


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
        write_owner_only(self.path, (json.dumps(saves, indent=2) + "\n").encode("utf-8"))

    def written_to(self, place_id: str) -> "NamesWrittenToPlace":
        return NamesWrittenToPlace(self, place_id)

    def _saves(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}


class NamesWrittenToPlace:
    def __init__(self, record: SaveRecord, place_id: str):
        self.record = record
        self.place_id = place_id

    def names(self) -> set[str]:
        return set(self.record.last(self.place_id).get("written", []))

    def remember(self, names: set[str]) -> None:
        self.record.note(self.place_id, written=sorted(names))
