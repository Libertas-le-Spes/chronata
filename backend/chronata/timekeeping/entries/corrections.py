from dataclasses import dataclass, replace
from datetime import datetime
from typing import ClassVar

from chronata.timekeeping.entries.new_entry import with_label, with_note
from chronata.timekeeping.entries.wording import detail, quoted
from chronata.timekeeping.record.record import Entry
from chronata.timekeeping.shifts.shifts import Correction, Happening, Shift


@dataclass(frozen=True)
class ShiftAdded:
    kind: ClassVar[str] = "shift_added"
    start: datetime
    end: datetime
    reason: str
    label: str = ""
    note: str | None = None

    def data(self) -> dict:
        return with_note({"start": self.start.isoformat(), "end": self.end.isoformat(), "reason": self.reason, **with_label(self.label)}, self.note)

    @staticmethod
    def apply(found: dict[int, Shift], entry: Entry) -> None:
        data = entry.data
        end = datetime.fromisoformat(data["end"])
        shift = Shift(entry.seq, datetime.fromisoformat(data["start"]), end, entry.recorded_at - end, data.get("label", ""))
        shift.changes.append(f"{entry.recorded_at:%Y-%m-%d %H:%M} written after the fact: {data['reason']}")
        shift.added_later = True
        span = f"{shift.start:%H:%M:%S} – {end:%H:%M:%S}"
        written = f"written down {entry.recorded_at:%a %d %b %H:%M}"
        shift.happenings.append(Happening(shift.start, "Added later", detail(span, written, quoted(data["reason"]), quoted(data.get("note")))))
        found[entry.seq] = shift


@dataclass(frozen=True)
class ShiftCorrected:
    kind: ClassVar[str] = "shift_corrected"
    shift: int
    start: datetime
    end: datetime
    reason: str

    def data(self) -> dict:
        return {"shift": self.shift, "start": self.start.isoformat(), "end": self.end.isoformat(), "reason": self.reason}

    @staticmethod
    def apply(found: dict[int, Shift], entry: Entry) -> None:
        data = entry.data
        shift = found[data["shift"]]
        start, end = datetime.fromisoformat(data["start"]), datetime.fromisoformat(data["end"])
        shift.changes.append(f"{entry.recorded_at:%Y-%m-%d %H:%M} changed {_span(shift.start, shift.end)} to {_span(start, end)}: {data['reason']}")
        shift.start, shift.end = start, end
        shift.corrections.append(Correction(entry.recorded_at, data["reason"]))


@dataclass(frozen=True)
class ShiftVoided:
    kind: ClassVar[str] = "shift_voided"
    shift: int
    reason: str

    def data(self) -> dict:
        return {"shift": self.shift, "reason": self.reason}

    @staticmethod
    def apply(found: dict[int, Shift], entry: Entry) -> None:
        shift = found[entry.data["shift"]]
        shift.voided = True
        shift.changes.append(f"{entry.recorded_at:%Y-%m-%d %H:%M} marked as a mistake: {entry.data['reason']}")
        shift.happenings.append(Happening(entry.recorded_at, "Marked as a mistake", quoted(entry.data["reason"])))


@dataclass(frozen=True)
class BreakExplained:
    kind: ClassVar[str] = "break_explained"
    shift: int
    start: str
    reason: str

    def data(self) -> dict:
        return {"shift": self.shift, "start": self.start, "reason": self.reason}

    @staticmethod
    def apply(found: dict[int, Shift], entry: Entry) -> None:
        data = entry.data
        shift = found[data["shift"]]
        started = datetime.fromisoformat(data["start"])
        shift.breaks = [replace(b, reason=data["reason"]) if b.start == started else b for b in shift.breaks]
        shift.changes.append(f"reason for the break at {started:%H:%M}: {data['reason']}")
        shift.happenings.append(Happening(started, "Why the PC was off", quoted(data["reason"])))


def _span(start: datetime, end: datetime | None) -> str:
    return f"{start:%Y-%m-%d %H:%M:%S}–{end:%H:%M:%S}" if end else f"{start:%Y-%m-%d %H:%M:%S}–open"
