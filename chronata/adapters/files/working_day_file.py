import json
from dataclasses import replace
from datetime import time, timedelta
from pathlib import Path

from chronata.timekeeping.working_day import WEEKDAY_NAMES, WorkingDay

DEFAULTS = {
    "shift": {"start": "08:00", "end": "17:00"},
    "lunch": {"start": "12:00", "minutes": 60},
    "workdays": ["mon", "tue", "wed", "thu", "fri"],
}


class WorkingDayFile:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> WorkingDay:
        saved = self._saved()
        configured = "shift" in saved and "lunch" in saved
        raw = {**DEFAULTS, **saved} if configured else {**DEFAULTS, "workdays": saved.get("workdays", DEFAULTS["workdays"])}
        workdays = frozenset(WEEKDAY_NAMES.index(day.lower()[:3]) for day in raw["workdays"])
        working_day = WorkingDay(
            time.fromisoformat(raw["shift"]["start"]),
            time.fromisoformat(raw["shift"]["end"]),
            time.fromisoformat(raw["lunch"]["start"]),
            int(raw["lunch"]["minutes"]),
            workdays,
            0.0,
            configured,
        )
        return replace(
            working_day,
            weekly_hours=float(raw.get("weekly_hours") or working_day.daily_hours * len(workdays)),
            early_leave_grace=timedelta(minutes=int(raw.get("early_leave_minutes", 7))),
        )

    def save(self, shift_start: time, shift_end: time, lunch_start: time, lunch_minutes: int) -> None:
        saved = self._saved()
        updated = {
            **saved,
            "shift": {"start": f"{shift_start:%H:%M}", "end": f"{shift_end:%H:%M}"},
            "lunch": {"start": f"{lunch_start:%H:%M}", "minutes": lunch_minutes},
            "workdays": saved.get("workdays", DEFAULTS["workdays"]),
        }
        self.path.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")

    def _saved(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
