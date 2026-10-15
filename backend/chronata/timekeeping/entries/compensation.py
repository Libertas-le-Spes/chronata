from dataclasses import dataclass
from datetime import date
from typing import ClassVar

from chronata.timekeeping.entries.new_entry import with_label

PAID = "paid"
TIME_OFF = "time_off"


@dataclass(frozen=True)
class Compensated:
    kind: ClassVar[str] = "compensation"
    start: date
    end: date
    hours: float
    time_off: bool
    reference: str = ""
    label: str = ""

    def data(self) -> dict:
        return {"from": self.start.isoformat(), "to": self.end.isoformat(), "hours": self.hours, **with_label(self.label),
                "kind": TIME_OFF if self.time_off else PAID, "reference": self.reference}
