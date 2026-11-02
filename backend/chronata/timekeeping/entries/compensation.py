from dataclasses import dataclass
from datetime import date
from typing import ClassVar

from chronata.timekeeping.compensation.given import Given, given_in
from chronata.timekeeping.entries.new_entry import with_label
from chronata.timekeeping.record.record import Entry


@dataclass(frozen=True)
class Compensated:
    kind: ClassVar[str] = "compensation"
    start: date
    end: date
    given: Given
    label: str = ""

    def data(self) -> dict:
        return {"from": self.start.isoformat(), "to": self.end.isoformat(), "hours": self.given.hours, **with_label(self.label),
                "kind": self.given.kind, "reference": self.given.reference}

    @staticmethod
    def of(entry: Entry) -> "Compensated":
        data = entry.data
        return Compensated(date.fromisoformat(data["from"]), date.fromisoformat(data["to"]), given_in(data), data.get("label", ""))
