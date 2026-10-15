from dataclasses import dataclass
from typing import ClassVar

from chronata.timekeeping.record import Entry
from chronata.timekeeping.shifts import Shift


@dataclass(frozen=True)
class ShiftLabelled:
    kind: ClassVar[str] = "shift_labelled"
    shift: int
    label: str
    reason: str = ""

    def data(self) -> dict:
        return {"shift": self.shift, "label": self.label, **({"reason": self.reason} if self.reason else {})}

    @staticmethod
    def apply(found: dict[int, Shift], entry: Entry) -> None:
        shift = found[entry.data["shift"]]
        if shift.label:
            shift.changes.append(f"{entry.recorded_at:%Y-%m-%d %H:%M} label changed from {shift.label} to {entry.data['label'] or 'none'}")
        shift.label = entry.data["label"]
