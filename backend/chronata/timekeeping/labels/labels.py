import unicodedata
from dataclasses import dataclass
from datetime import datetime
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
