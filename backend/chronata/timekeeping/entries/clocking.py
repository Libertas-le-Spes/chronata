from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar

from chronata.timekeeping.entries.new_entry import with_label, with_note
from chronata.timekeeping.entries.wording import detail, quoted
from chronata.timekeeping.record.record import Entry
from chronata.timekeeping.shifts.shifts import Break, CLOCKED_OUT, Happening, Shift

MANUAL_CLOCK_IN = "Manual clock in"
MANUAL_CLOCK_OUT = "Manual clock out"
SAME_MOMENT = timedelta(minutes=1)


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
        shift = Shift(entry.seq, start, None, entry.recorded_at - start, entry.data.get("label", ""))
        counted_from = f"counted from {start:%H:%M:%S}" if entry.recorded_at - start >= SAME_MOMENT else ""
        shift.happenings.append(Happening(entry.recorded_at, MANUAL_CLOCK_IN, detail(counted_from, quoted(entry.data.get("note")))))
        found[entry.seq] = shift


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
        not_counted = f"{gap.start:%H:%M}–{gap.end:%H:%M} not counted"
        shift.happenings.append(Happening(gap.end, MANUAL_CLOCK_IN, detail(not_counted, quoted(entry.data.get("note")))))
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
        shift.happenings.append(Happening(shift.end, MANUAL_CLOCK_OUT, quoted(entry.data.get("note"))))
        shift.entered_late_by = max(shift.entered_late_by, entry.recorded_at - shift.end)
