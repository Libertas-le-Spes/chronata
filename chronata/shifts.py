from dataclasses import dataclass, field
from datetime import datetime, timedelta

from chronata.ledger import Entry


@dataclass
class Shift:
    id: int
    start: datetime
    end: datetime | None
    entered_late_by: timedelta
    notes: list[str] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)
    voided: bool = False

    @property
    def duration(self) -> timedelta | None:
        return self.end - self.start if self.end else None


def shifts(entries: list[Entry]) -> list[Shift]:
    found: dict[int, Shift] = {}
    for entry in entries:
        data = entry.data
        match entry.kind:
            case "clock_in":
                start = datetime.fromisoformat(data["at"])
                found[entry.seq] = Shift(entry.seq, start, None, entry.recorded_at - start)
            case "clock_out":
                shift = found[data["shift"]]
                shift.end = datetime.fromisoformat(data["at"])
                shift.entered_late_by = max(shift.entered_late_by, entry.recorded_at - shift.end)
            case "shift_added":
                end = datetime.fromisoformat(data["end"])
                shift = Shift(entry.seq, datetime.fromisoformat(data["start"]), end, entry.recorded_at - end)
                shift.changes.append(f"{entry.recorded_at:%Y-%m-%d %H:%M} written after the fact: {data['reason']}")
                found[entry.seq] = shift
            case "shift_corrected":
                shift = found[data["shift"]]
                start, end = datetime.fromisoformat(data["start"]), datetime.fromisoformat(data["end"])
                shift.changes.append(
                    f"{entry.recorded_at:%Y-%m-%d %H:%M} changed {_span(shift.start, shift.end)} to {_span(start, end)}: {data['reason']}"
                )
                shift.start, shift.end = start, end
            case "shift_voided":
                shift = found[data["shift"]]
                shift.voided = True
                shift.changes.append(f"{entry.recorded_at:%Y-%m-%d %H:%M} struck out: {data['reason']}")
            case _:
                continue
        if data.get("note"):
            found[data.get("shift", entry.seq)].notes.append(data["note"])
    return sorted(found.values(), key=lambda shift: shift.start)


def open_shift(all_shifts: list[Shift]) -> Shift | None:
    return next((shift for shift in all_shifts if shift.end is None and not shift.voided), None)


def completed(all_shifts: list[Shift]) -> list[Shift]:
    return [shift for shift in all_shifts if shift.end is not None and not shift.voided]


def _span(start: datetime, end: datetime | None) -> str:
    return f"{start:%Y-%m-%d %H:%M:%S}–{end:%H:%M:%S}" if end else f"{start:%Y-%m-%d %H:%M:%S}–open"
