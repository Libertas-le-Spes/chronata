import json
from datetime import timedelta
from pathlib import Path

from chronata.adapters.storage.owner_only_file import write_owner_only
from chronata.use_cases.reminders.reminder_pace import ReminderPace
from chronata.use_cases.reminders.reminder_setting import FEWEST_MINUTES, MOST_MINUTES

CLOCK_OUT_EVERY = "clock_out_every_minutes"


class ReminderPaceFile:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> ReminderPace:
        if not self.path.exists():
            return ReminderPace()
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
        except ValueError:
            return ReminderPace()
        return _pace_in(saved)

    def save(self, pace: ReminderPace) -> None:
        write_owner_only(self.path, (json.dumps({CLOCK_OUT_EVERY: _minutes(pace)}, indent=2) + "\n").encode("utf-8"))


def _pace_in(saved) -> ReminderPace:
    if not isinstance(saved, dict) or CLOCK_OUT_EVERY not in saved:
        return ReminderPace()
    minutes = saved[CLOCK_OUT_EVERY]
    if minutes is None:
        return ReminderPace(None)
    if not isinstance(minutes, int):
        return ReminderPace()
    if not FEWEST_MINUTES <= minutes <= MOST_MINUTES:
        return ReminderPace()
    return ReminderPace(timedelta(minutes=minutes))


def _minutes(pace: ReminderPace) -> int | None:
    if pace.off:
        return None
    return round(pace.every.total_seconds() / 60)
