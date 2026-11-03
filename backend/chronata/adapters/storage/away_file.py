import json
from datetime import datetime

from chronata.adapters.storage.owner_only_folder import OwnerOnlyFolder
from chronata.use_cases.away.away_stretch import AwayStretch
from chronata.use_cases.log.ports import NotPrivate

AWAY = "away.json"


class AwayFile:
    def __init__(self, folder: OwnerOnlyFolder):
        self.folder = folder

    def load(self) -> AwayStretch | None:
        try:
            text = self.folder.read(AWAY)
        except (NotPrivate, OSError, ValueError):
            return None
        if text is None:
            return None
        try:
            return _stretch_in(json.loads(text))
        except (ValueError, TypeError, KeyError, RecursionError):
            return None

    def keep(self, stretch: AwayStretch) -> None:
        self.folder.write(AWAY, json.dumps({"shift": stretch.shift, "since": stretch.since.isoformat(), "back": _iso(stretch.back)}))

    def forget(self) -> None:
        self.folder.forget(AWAY)


def _stretch_in(saved: dict) -> AwayStretch | None:
    shift = saved["shift"]
    if not isinstance(shift, int):
        return None
    return AwayStretch(shift, _moment(saved["since"]), _optional_moment(saved["back"]))


def _moment(text: str) -> datetime:
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        raise ValueError("a time without its zone")
    return moment


def _optional_moment(text: str | None) -> datetime | None:
    if text is None:
        return None
    return _moment(text)


def _iso(moment: datetime | None) -> str | None:
    if moment is None:
        return None
    return moment.isoformat()
