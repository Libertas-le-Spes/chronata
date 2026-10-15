from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from chronata.timekeeping.entries.new_entry import with_label, with_note
from chronata.timekeeping.record.record import Entry
from chronata.timekeeping.shifts.shifts import Break, CLOCKED_OUT, Shift


@dataclass(frozen=True)
class ClockIn:
    kind: ClassVar[str] = "clock_in"
    at: datetime
    boot: str
    label: str = ""
    note: str | None = None

    def data(self) -> dict:
        return with_note({"at": self.at.isoformat(), "boot": self.boot, **with_label(self.label)}, self.note)

    @staticmethod
    def apply(found: dict[int, Shift], entry: Entry) -> None:
        start = datetime.fromisoformat(entry.data["at"])
        found[entry.seq] = Shift(entry.seq, start, None, entry.recorded_at - start, entry.data.get("label", ""))


@dataclass(frozen=True)
class ClockResumed:
    kind: ClassVar[str] = "clock_resumed"
    shift: int
    at: datetime
    boot: str
    note: str | None = None

    def data(self) -> dict:
        return with_note({"shift": self.shift, "at": self.at.isoformat(), "boot": self.boot}, self.note)

    @staticmethod
    def apply(found: dict[int, Shift], entry: Entry) -> None:
        shift = found[entry.data["shift"]]
        gap = Break(shift.end, datetime.fromisoformat(entry.data["at"]), CLOCKED_OUT)
        shift.breaks.append(gap)
        shift.changes.append(f"break {gap.start:%H:%M:%S}–{gap.end:%H:%M:%S}, not counted as work")
        shift.end = None


@dataclass(frozen=True)
class ClockOut:
    kind: ClassVar[str] = "clock_out"
    shift: int
    at: datetime
    boot: str
    note: str | None = None

    def data(self) -> dict:
        return with_note({"shift": self.shift, "at": self.at.isoformat(), "boot": self.boot}, self.note)

    @staticmethod
    def apply(found: dict[int, Shift], entry: Entry) -> None:
        shift = found[entry.data["shift"]]
        shift.end = datetime.fromisoformat(entry.data["at"])
        shift.entered_late_by = max(shift.entered_late_by, entry.recorded_at - shift.end)
