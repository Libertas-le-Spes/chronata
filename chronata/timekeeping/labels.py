from dataclasses import dataclass
from difflib import get_close_matches

from chronata.timekeeping.shifts import Shift


@dataclass(frozen=True)
class LabelChoice:
    label: str
    exists: bool
    near_misses: tuple[str, ...]


def known_labels(all_shifts: list[Shift]) -> list[str]:
    recent = sorted((s for s in all_shifts if s.label and not s.voided), key=lambda s: s.start, reverse=True)
    return list(dict.fromkeys(s.label for s in recent))


def tidy(typed: str) -> str:
    return " ".join(typed.split())


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
