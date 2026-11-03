from dataclasses import dataclass
from typing import ClassVar

from chronata.timekeeping.record.record import Entry
from chronata.timekeeping.shifts.shifts import Happening, Shift

RENAMED_FROM = "renamed_from"
RENAMED_TO = "renamed_to"


@dataclass(frozen=True)
class ShiftLabelled:
    kind: ClassVar[str] = "shift_labelled"
    shift: int
    label: str
    reason: str = ""
    renamed_from: str = ""
    renamed_to: str = ""

    def data(self) -> dict:
        data = {"shift": self.shift, "label": self.label}
        if self.reason:
            data["reason"] = self.reason
        if self.renamed_from:
            data[RENAMED_FROM] = self.renamed_from
            data[RENAMED_TO] = self.renamed_to
        return data

    @staticmethod
    def apply(found: dict[int, Shift], entry: Entry) -> None:
        shift = found[entry.data["shift"]]
        new_label = entry.data["label"]
        if shift.label:
            shift.changes.append(f"{entry.recorded_at:%Y-%m-%d %H:%M} label changed from {shift.label} to {_shown(new_label)}")
            shift.happenings.append(Happening(entry.recorded_at, "Label changed", f"from {shift.label} to {_shown(new_label)}"))
        shift.label = new_label
        if _text(entry.data.get(RENAMED_FROM)):
            shift.start_answer = shift.start_answer.renamed(entry.data[RENAMED_FROM], _text(entry.data.get(RENAMED_TO)))


def _text(stored) -> str:
    if isinstance(stored, str):
        return stored
    return ""


def _shown(label: str) -> str:
    if label:
        return label
    return "none"
