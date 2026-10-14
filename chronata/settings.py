import json
import os
from dataclasses import replace
from datetime import time
from pathlib import Path

from chronata.rules import Rules

DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
RULES_FILE = "rules.json"

DEFAULT_RULES = {
    "shift": {"start": "08:00", "end": "17:00"},
    "lunch": {"start": "12:00", "minutes": 60},
    "workdays": ["mon", "tue", "wed", "thu", "fri"],
}


def data_dir() -> Path:
    return Path(os.environ.get("CHRONATA_HOME", Path.home() / ".local" / "share" / "chronata"))


def load_rules(directory: Path) -> Rules:
    path = directory / RULES_FILE
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    configured = "shift" in saved and "lunch" in saved
    raw = {**DEFAULT_RULES, **saved} if configured else {**DEFAULT_RULES, "workdays": saved.get("workdays", DEFAULT_RULES["workdays"])}
    workdays = frozenset(DAY_NAMES.index(day.lower()[:3]) for day in raw["workdays"])
    rules = Rules(
        time.fromisoformat(raw["shift"]["start"]),
        time.fromisoformat(raw["shift"]["end"]),
        time.fromisoformat(raw["lunch"]["start"]),
        int(raw["lunch"]["minutes"]),
        workdays,
        0.0,
        configured,
    )
    return replace(rules, weekly_hours=float(raw.get("weekly_hours") or rules.daily_hours * len(workdays)))


def save_rules(directory: Path, shift_start: time, shift_end: time, lunch_start: time, lunch_minutes: int) -> None:
    path = directory / RULES_FILE
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    rules = {
        "shift": {"start": f"{shift_start:%H:%M}", "end": f"{shift_end:%H:%M}"},
        "lunch": {"start": f"{lunch_start:%H:%M}", "minutes": lunch_minutes},
        "workdays": saved.get("workdays", DEFAULT_RULES["workdays"]),
    }
    path.write_text(json.dumps(rules, indent=2) + "\n", encoding="utf-8")
