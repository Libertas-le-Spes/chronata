import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import get_close_matches

from chronata.timekeeping.shifts.shifts import Shift
from chronata.timekeeping.shifts.today import resumable

CONTROLS = {"Cc", "Cs", "Co"}
DIRECTION_OVERRIDES = {chr(code) for code in (*range(0x202A, 0x202F), *range(0x2066, 0x206A))}


@dataclass(frozen=True)
class LabelChoice:
    label: str
    exists: bool
    near_misses: tuple[str, ...]


@dataclass(frozen=True)
class LabelHours:
    label: str
    this_week: timedelta
    all_time: timedelta
    open_now: bool


def hours_by_label(all_shifts: list[Shift], now: datetime) -> list[LabelHours]:
    monday = now.date() - timedelta(days=now.weekday())
    week: dict[str, timedelta] = {}
    total: dict[str, timedelta] = {}
    open_now: set[str] = set()
    for shift in (s for s in all_shifts if not s.voided):
        worked = shift.worked(shift.end or now)
        total[shift.label] = total.get(shift.label, timedelta()) + worked
        if shift.start.date() >= monday:
            week[shift.label] = week.get(shift.label, timedelta()) + worked
        if shift.end is None:
            open_now.add(shift.label)
    return [LabelHours(label, week.get(label, timedelta()), worked, label in open_now)
            for label, worked in sorted(total.items(), key=lambda item: item[1], reverse=True)]


def known_labels(all_shifts: list[Shift]) -> list[str]:
    recent = sorted((s for s in all_shifts if s.label and not s.voided), key=lambda s: s.start, reverse=True)
    return list(dict.fromkeys(s.label for s in recent))


def suggested(all_shifts: list[Shift], now: datetime, default_label: str) -> str:
    earlier_today = resumable(all_shifts, now)
    if earlier_today:
        return earlier_today.label
    recent = known_labels(all_shifts)
    return default_label or (recent[0] if recent else "")


def tidy(typed: str) -> str:
    kept = (character for character in typed if unicodedata.category(character) not in CONTROLS and character not in DIRECTION_OVERRIDES)
    return " ".join("".join(kept).split())


def choose(typed: str, known: list[str]) -> LabelChoice:
    label = tidy(typed)
    if not label:
        return LabelChoice("", True, ())
    same = next((existing for existing in known if _key(existing) == _key(label)), None)
    if same:
        return LabelChoice(same, True, ())
    close = get_close_matches(_key(label), [_key(existing) for existing in known], n=3, cutoff=0.75)
    return LabelChoice(label, False, tuple(existing for existing in known if _key(existing) in close))


def _key(label: str) -> str:
    return tidy(label).casefold()
