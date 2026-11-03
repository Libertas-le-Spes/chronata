import json
import os
import stat
from datetime import timedelta
from pathlib import Path

from chronata.adapters.storage.owner_only_file import write_owner_only
from chronata.timekeeping.shifts.durations import minutes
from chronata.use_cases.reminders.reminder_pace import ReminderPace, allowed_minutes

CLOCK_OUT_EVERY = "clock_out_every_minutes"
MOST_BYTES = 4096


class ReminderPaceFile:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> ReminderPace:
        text = _own_regular_file(self.path)
        if text is None:
            return ReminderPace()
        try:
            saved = json.loads(text)
        except (ValueError, RecursionError):
            return ReminderPace()
        return _pace_in(saved)

    def save(self, pace: ReminderPace) -> None:
        write_owner_only(self.path, (json.dumps({CLOCK_OUT_EVERY: _minutes(pace)}, indent=2) + "\n").encode("utf-8"))


def _own_regular_file(path: Path) -> str | None:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        return None
    try:
        return _contents(descriptor)
    finally:
        os.close(descriptor)


def _contents(descriptor: int) -> str | None:
    if not _safe_to_read(os.fstat(descriptor)):
        return None
    try:
        return os.read(descriptor, MOST_BYTES + 1).decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _safe_to_read(status: os.stat_result) -> bool:
    if not stat.S_ISREG(status.st_mode):
        return False
    if status.st_uid != os.getuid():
        return False
    return status.st_size <= MOST_BYTES


def _pace_in(saved) -> ReminderPace:
    if not isinstance(saved, dict) or CLOCK_OUT_EVERY not in saved:
        return ReminderPace()
    given = saved[CLOCK_OUT_EVERY]
    if given is None:
        return ReminderPace(None)
    if not allowed_minutes(given):
        return ReminderPace()
    return ReminderPace(timedelta(minutes=given))


def _minutes(pace: ReminderPace) -> int | None:
    if pace.off:
        return None
    return minutes(pace.every)
