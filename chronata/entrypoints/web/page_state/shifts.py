from datetime import datetime, timedelta

from chronata.entrypoints.web.page_state.snapshot import Snapshot
from chronata.presenters.text_report import LATE_ENOUGH_TO_FLAG
from chronata.timekeeping.durations import minutes
from chronata.timekeeping.pc_sessions import PcSession, support
from chronata.timekeeping.shifts import Shift
from chronata.timekeeping.stamps import Stamp
from chronata.timekeeping.start_proof import start_proof


def state(app, taken: Snapshot) -> dict:
    stamps = app.timestamper.stamps()
    newest_day_first = sorted(taken.shifts, key=lambda s: (-s.start.date().toordinal(), s.start))
    return {
        "weeks": [
            {"start": week.start.isoformat(), "end": week.end.isoformat(), "worked": minutes(week.worked),
             "overtime": minutes(week.overtime), "running": week.end >= taken.now.date()}
            for week in reversed(taken.weeks)
        ],
        "shifts": [_shift(shift, taken.sessions, stamps, taken.now) for shift in newest_day_first],
        "days": {
            day.date.isoformat(): {"late": minutes(day.late), "short": minutes(day.short), "madeUp": day.made_up, "lastOut": day.last_out.isoformat()}
            for week in taken.weeks for day in week.days if day.late > timedelta() or day.short > timedelta()
        },
        "unexplainedBreaks": [
            {"shift": shift.id, "start": gap.start.isoformat(), "end": gap.end.isoformat()}
            for shift in taken.shifts for gap in shift.breaks if gap.cause == "PC off" and not gap.reason
        ],
    }


def _shift(shift: Shift, sessions: list[PcSession], stamps: list[Stamp], now: datetime) -> dict:
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
