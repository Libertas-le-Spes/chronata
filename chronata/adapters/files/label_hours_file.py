import json
from datetime import time, timedelta
from pathlib import Path

from chronata.timekeeping.label_hours import LabelHours
from chronata.timekeeping.working_day import MONDAY_TO_FRIDAY, WEEKDAY_NAMES, Lunch, WorkingDay


class LabelHoursFile:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> LabelHours:
        saved = self._saved()
        return LabelHours(saved.get("default_label", ""), {label: _hours(raw) for label, raw in saved.get("labels", {}).items()})

    def save_hours(self, label: str, hours: WorkingDay | None) -> None:
        saved = self._saved()
        self._write({**saved, "labels": {**saved.get("labels", {}), label: _raw(hours)}})

    def save_default_label(self, label: str) -> None:
        saved = {key: value for key, value in self._saved().items() if key != "default_label"}
        self._write({**saved, "default_label": label} if label else saved)

    def rename(self, old: str, new: str) -> None:
        saved = self._saved()
        labels = dict(saved.get("labels", {}))
        if old in labels:
            moved = labels.pop(old)
            labels.setdefault(new, moved)
        self._write({**saved, "labels": labels})

    def _write(self, rules: dict) -> None:
        self.path.write_text(json.dumps(rules, indent=2) + "\n", encoding="utf-8")

    def _saved(self) -> dict:
        saved = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        return _from_one_set_of_hours(saved) if "labels" not in saved else saved


def _from_one_set_of_hours(saved: dict) -> dict:
    rules = {key: saved[key] for key in ("default_label",) if key in saved}
    if "shift" not in saved:
        return {**rules, "labels": {}}
    hours = {key: saved[key] for key in ("shift", "lunch", "workdays", "weekly_hours", "early_leave_minutes") if key in saved}
    return {**rules, "labels": {saved.get("default_label", ""): hours}}


def _hours(raw: dict | None) -> WorkingDay | None:
    if raw is None:
        return None
    lunch = raw.get("lunch")
    workdays = frozenset(WEEKDAY_NAMES.index(day.lower()[:3]) for day in raw["workdays"]) if "workdays" in raw else MONDAY_TO_FRIDAY
    return WorkingDay(
        time.fromisoformat(raw["shift"]["start"]),
        time.fromisoformat(raw["shift"]["end"]),
        Lunch(time.fromisoformat(lunch["start"]), int(lunch["minutes"])) if lunch else None,
        workdays,
        float(raw["weekly_hours"]) if raw.get("weekly_hours") else None,
        timedelta(minutes=int(raw.get("early_leave_minutes", 7))),
    )


def _raw(hours: WorkingDay | None) -> dict | None:
    if hours is None:
        return None
    raw = {
        "shift": {"start": f"{hours.shift_start:%H:%M}", "end": f"{hours.shift_end:%H:%M}"},
        "lunch": {"start": f"{hours.lunch.start:%H:%M}", "minutes": hours.lunch.minutes} if hours.lunch else None,
        "workdays": [WEEKDAY_NAMES[day] for day in sorted(hours.workdays)],
    }
    if hours.weekly_limit:
        raw["weekly_hours"] = hours.weekly_limit
    if hours.early_leave_grace != timedelta(minutes=7):
        raw["early_leave_minutes"] = int(hours.early_leave_grace / timedelta(minutes=1))
    return raw
