from dataclasses import dataclass, field
from datetime import datetime, timedelta

from chronata.ledger import Entry

@dataclass(frozen=True)
class Break:
    start: datetime
    end: datetime


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
                resumed = datetime.fromisoformat(data["at"])
                gap = Break(shift.end, resumed)
                shift.breaks.append(gap)
                shift.changes.append(f"break {gap.start:%H:%M:%S}–{gap.end:%H:%M:%S}, not counted as work")
                shift.end = None
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


def labels(all_shifts: list[Shift]) -> list[str]:
    recent = sorted((s for s in all_shifts if s.label), key=lambda s: s.start, reverse=True)
    return list(dict.fromkeys(s.label for s in recent))


def _span(start: datetime, end: datetime | None) -> str:
    return f"{start:%Y-%m-%d %H:%M:%S}–{end:%H:%M:%S}" if end else f"{start:%Y-%m-%d %H:%M:%S}–open"
