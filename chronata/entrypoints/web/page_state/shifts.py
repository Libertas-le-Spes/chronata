from datetime import datetime, timedelta

from chronata.entrypoints.web.page_state.snapshot import Snapshot
from chronata.presenters.explanation import LATE_ENOUGH_TO_FLAG
from chronata.timekeeping.day_entries import DayEntry, day_entries, pc_share
from chronata.timekeeping.durations import minutes
from chronata.timekeeping.overtime import Day, days_so_far
from chronata.timekeeping.pc_sessions import PcSession, support
from chronata.timekeeping.shifts import Shift
from chronata.timekeeping.stamps import Stamp
from chronata.timekeeping.start_proof import start_proof


def state(app, taken: Snapshot) -> dict:
    stamps = app.timestamper.stamps()
    days = days_so_far(taken.shifts, taken.hours, taken.now)
    newest_day_first = sorted(day_entries(taken.shifts), key=lambda e: (-e.day.toordinal(), e.start))
    return {
        "weeks": [
            {"start": week.start.isoformat(), "end": week.end.isoformat(), "worked": minutes(week.worked),
             "overtime": minutes(week.overtime), "running": week.end >= taken.now.date()}
            for week in reversed(taken.weeks)
        ],
        "entries": [_entry(entry, days.get((entry.day, entry.label or taken.hours.default_label)), taken.sessions, stamps, taken.now)
                    for entry in newest_day_first],
        "unexplainedBreaks": [
            {"shift": shift.id, "start": gap.start.isoformat(), "end": gap.end.isoformat()}
            for shift in taken.shifts for gap in shift.breaks if gap.cause == "PC off" and not gap.reason
        ],
    }


def _entry(entry: DayEntry, day: Day | None, sessions: list[PcSession], stamps: list[Stamp], now: datetime) -> dict:
    flagged = day is not None and (day.late > timedelta() or day.short > timedelta())
    return {
        "day": entry.day.isoformat(),
        "label": entry.label,
        "start": entry.start.isoformat(),
        "end": entry.end.isoformat() if entry.end else None,
        "worked": minutes(entry.worked(now)),
        "voided": entry.voided,
        "pcShare": pc_share(entry, sessions, now),
        "punctuality": {"late": minutes(day.late), "short": minutes(day.short), "madeUp": day.made_up, "running": day.running, "lastOut": day.last_out.isoformat()} if flagged else None,
        "pieces": [_piece(piece, sessions, stamps, now) for piece in entry.pieces],
    }


def _piece(shift: Shift, sessions: list[PcSession], stamps: list[Stamp], now: datetime) -> dict:
    backing = support(shift.start, shift.end, sessions, now)
    proof = start_proof(shift, sessions, stamps)
    return {
        "id": shift.id,
        "label": shift.label,
        "start": shift.start.isoformat(),
        "end": shift.end.isoformat() if shift.end else None,
        "since": shift.since.isoformat(),
        "worked": minutes(shift.worked(now)),
        "voided": shift.voided,
        "lateBy": minutes(shift.entered_late_by) if shift.entered_late_by > LATE_ENOUGH_TO_FLAG else None,
        "notes": shift.notes,
        "changes": shift.changes,
        "proof": {
            "fromPcOn": proof.from_pc_on,
            "entry": proof.entry,
            "stamps": [{"authority": s.authority_name, "time": s.time.astimezone(shift.start.tzinfo).isoformat()} for s in proof.stamps],
        },
        "pc": {
            "share": round(backing.share, 3),
            "beforeRecords": backing.before_records,
            "sessions": [{"on": s.on.isoformat(), "off": s.off.isoformat() if s.off else None, "exact": s.exact} for s in backing.sessions],
        },
    }
