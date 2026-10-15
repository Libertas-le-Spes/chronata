from dataclasses import replace
from datetime import datetime

from chronata.timekeeping.record import Entry
from chronata.timekeeping.shifts import CLOCKED_OUT, PC_OFF, Break, Shift


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
                gap = Break(shift.end, datetime.fromisoformat(data["at"]), CLOCKED_OUT)
                shift.breaks.append(gap)
                shift.changes.append(f"break {gap.start:%H:%M:%S}–{gap.end:%H:%M:%S}, not counted as work")
                shift.end = None
            case "pc_off_break":
                gap = Break(datetime.fromisoformat(data["start"]), datetime.fromisoformat(data["end"]), PC_OFF)
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


def _span(start: datetime, end: datetime | None) -> str:
    return f"{start:%Y-%m-%d %H:%M:%S}–{end:%H:%M:%S}" if end else f"{start:%Y-%m-%d %H:%M:%S}–open"
