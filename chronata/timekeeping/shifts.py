from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from chronata.timekeeping.record import Entry

UNCLOCKED_WORTH_ASKING = timedelta(minutes=5)


@dataclass(frozen=True)
class Break:
    start: datetime
    end: datetime
    cause: str
    reason: str = ""


@dataclass
class Shift:
    id: int
    start: datetime
    end: datetime | None
    entered_late_by: timedelta
    label: str = ""
    breaks: list[Break] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)
    voided: bool = False

    @property
    def since(self) -> datetime:
        return self.breaks[-1].end if self.breaks else self.start

    def worked(self, until: datetime) -> timedelta:
        return sum((ends - begins for begins, ends in self.segments(until)), timedelta())

    def segments(self, until: datetime) -> list[tuple[datetime, datetime]]:
        finish = self.end or until
        pieces, cursor = [], self.start
        for gap in self.breaks:
            pieces.append((cursor, gap.start))
            cursor = gap.end
        pieces.append((cursor, finish))
        return [(begins, ends) for begins, ends in pieces if ends > begins]


def shifts(entries: list[Entry]) -> list[Shift]:
    found: dict[int, Shift] = {}
    for entry in entries:
        data = entry.data
        match entry.kind:
            case "clock_in":
                start = datetime.fromisoformat(data["at"])
                found[entry.seq] = Shift(entry.seq, start, None, entry.recorded_at - start, data.get("label", ""))
            case "clock_out":
                shift = found[data["shift"]]
                shift.end = datetime.fromisoformat(data["at"])
                shift.entered_late_by = max(shift.entered_late_by, entry.recorded_at - shift.end)
            case "clock_resumed":
                shift = found[data["shift"]]
                gap = Break(shift.end, datetime.fromisoformat(data["at"]), "clocked out")
                shift.breaks.append(gap)
                shift.changes.append(f"break {gap.start:%H:%M:%S}–{gap.end:%H:%M:%S}, not counted as work")
                shift.end = None
            case "pc_off_break":
                gap = Break(datetime.fromisoformat(data["start"]), datetime.fromisoformat(data["end"]), "PC off")
                shift = found[data["shift"]]
                shift.breaks.append(gap)
                shift.changes.append(f"PC off {gap.start:%H:%M:%S}–{gap.end:%H:%M:%S}, not counted as work")
            case "break_explained":
                shift = found[data["shift"]]
                started = datetime.fromisoformat(data["start"])
                shift.breaks = [replace(b, reason=data["reason"]) if b.start == started else b for b in shift.breaks]
                shift.changes.append(f"reason for the break at {started:%H:%M}: {data['reason']}")
            case "shift_added":
                end = datetime.fromisoformat(data["end"])
                shift = Shift(entry.seq, datetime.fromisoformat(data["start"]), end, entry.recorded_at - end, data.get("label", ""))
                shift.changes.append(f"{entry.recorded_at:%Y-%m-%d %H:%M} written after the fact: {data['reason']}")
                found[entry.seq] = shift
            case "shift_corrected":
                shift = found[data["shift"]]
                start, end = datetime.fromisoformat(data["start"]), datetime.fromisoformat(data["end"])
                shift.changes.append(
                    f"{entry.recorded_at:%Y-%m-%d %H:%M} changed {_span(shift.start, shift.end)} to {_span(start, end)}: {data['reason']}"
                )
                shift.start, shift.end = start, end
            case "shift_labelled":
                shift = found[data["shift"]]
                if shift.label:
                    shift.changes.append(f"{entry.recorded_at:%Y-%m-%d %H:%M} label changed from {shift.label} to {data['label'] or 'none'}")
                shift.label = data["label"]
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


def resumable(all_shifts: list[Shift], now: datetime) -> Shift | None:
    finished = [shift for shift in completed(all_shifts) if shift.end <= now]
    latest = max(finished, key=lambda shift: shift.end, default=None)
    return latest if latest and latest.start.date() == now.date() else None


def unclocked_since(all_shifts: list[Shift], pc_on: datetime | None, now: datetime) -> datetime | None:
    if pc_on is None or pc_on.date() != now.date() or now - pc_on < UNCLOCKED_WORTH_ASKING or open_shift(all_shifts):
        return None
    clocked_since_pc_on = any(shift.end > pc_on for shift in completed(all_shifts))
    return None if clocked_since_pc_on else pc_on


def unexplained_pc_breaks(all_shifts: list[Shift], day) -> list[tuple[Shift, Break]]:
    return [(shift, gap) for shift in all_shifts for gap in shift.breaks
            if gap.cause == "PC off" and not gap.reason and gap.start.date() == day]


def _span(start: datetime, end: datetime | None) -> str:
    return f"{start:%Y-%m-%d %H:%M:%S}–{end:%H:%M:%S}" if end else f"{start:%Y-%m-%d %H:%M:%S}–open"
