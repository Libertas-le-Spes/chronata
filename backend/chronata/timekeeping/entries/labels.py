from dataclasses import dataclass
from typing import ClassVar

from chronata.timekeeping.record.record import Entry
from chronata.timekeeping.shifts.shifts import Happening, Shift
from chronata.timekeeping.shifts.start_answer import StartAnswer

RENAMED = "renamed"


@dataclass(frozen=True)
class ShiftLabelled:
    kind: ClassVar[str] = "shift_labelled"
    shift: int
    label: str
    reason: str = ""
    renamed: bool = False

    def data(self) -> dict:
        data = {"shift": self.shift, "label": self.label}
        if self.reason:
            data["reason"] = self.reason
        if self.renamed:
            data[RENAMED] = True
        return data

    @staticmethod
    def apply(found: dict[int, Shift], entry: Entry) -> None:
        shift = found[entry.data["shift"]]
        new_label = entry.data["label"]
        if shift.label:
            shift.changes.append(f"{entry.recorded_at:%Y-%m-%d %H:%M} label changed from {shift.label} to {_shown(new_label)}")
            shift.happenings.append(Happening(entry.recorded_at, "Label changed", f"from {shift.label} to {_shown(new_label)}"))
        shift.label = new_label
        if entry.data.get(RENAMED) is not True:
            shift.start_answer = StartAnswer()


def _shown(label: str) -> str:
    if label:
        return label
    return "none"
