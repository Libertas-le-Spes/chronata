from datetime import datetime

from chronata.presenters.page.facts import PageFacts
from chronata.presenters.page.values import iso
from chronata.presenters.text.explanation import LATE_ENOUGH_TO_FLAG
from chronata.timekeeping.hours.overtime import Day, days_so_far
from chronata.timekeeping.pc.pc_sessions import PcSession, support
from chronata.timekeeping.pc.start_proof import start_proof
from chronata.timekeeping.record.stamps import Stamp
from chronata.timekeeping.shifts.day_entries import DayEntry, day_entries, pc_share
from chronata.timekeeping.shifts.durations import minutes
from chronata.timekeeping.shifts.shifts import Shift


def state(facts: PageFacts) -> dict:
    stamps = facts.stamps
    days = days_so_far(facts.shifts, facts.hours, facts.now)
    newest_day_first = sorted(day_entries(facts.shifts), key=lambda e: (-e.day.toordinal(), e.start))
    return {
        "weeks": [
            {"start": week.start.isoformat(), "end": week.end.isoformat(), "worked": minutes(week.worked),
             "overtime": minutes(week.overtime), "running": week.end >= facts.now.date()}
            for week in reversed(facts.weeks)
        ],
        "entries": [_entry(entry, days.get((entry.day, entry.label or facts.hours.default_label)), facts.sessions, stamps, facts.now)
                    for entry in newest_day_first],
        "unexplainedBreaks": [
            {"shift": shift.id, "start": gap.start.isoformat(), "end": gap.end.isoformat()}
            for shift in facts.shifts for gap in shift.breaks if gap.unexplained_pc_off
        ],
    }


def _entry(entry: DayEntry, day: Day | None, sessions: list[PcSession], stamps: list[Stamp], now: datetime) -> dict:
    return {
        "day": entry.day.isoformat(),
        "label": entry.label,
        "start": entry.start.isoformat(),
        "end": iso(entry.end),
        "worked": minutes(entry.worked(now)),
        "voided": entry.voided,
        "pcShare": pc_share(entry, sessions, now),
        "punctuality": _punctuality(day),
        "pieces": [_piece(piece, sessions, stamps, now) for piece in entry.pieces],
    }


def _punctuality(day: Day | None) -> dict | None:
    if day is None or not day.worth_noting:
        return None
    return {"late": minutes(day.late), "short": minutes(day.short), "madeUp": day.made_up, "running": day.running, "lastOut": day.last_out.isoformat()}


def _piece(shift: Shift, sessions: list[PcSession], stamps: list[Stamp], now: datetime) -> dict:
    return {
        "id": shift.id,
        "label": shift.label,
        "start": shift.start.isoformat(),
        "end": iso(shift.end),
        "since": shift.since.isoformat(),
        "worked": minutes(shift.worked(now)),
        "voided": shift.voided,
        "lateBy": minutes(shift.entered_late_by) if shift.entered_late_by > LATE_ENOUGH_TO_FLAG else None,
        "notes": shift.notes,
        "changes": shift.changes,
        "proof": _proof(shift, sessions, stamps),
        "pc": _pc(shift, sessions, now),
    }


def _proof(shift: Shift, sessions: list[PcSession], stamps: list[Stamp]) -> dict:
    proof = start_proof(shift, sessions, stamps)
    return {"fromPcOn": proof.from_pc_on, "entry": proof.entry,
            "stamps": [{"authority": s.authority_name, "time": s.time.astimezone(shift.start.tzinfo).isoformat()} for s in proof.stamps]}


def _pc(shift: Shift, sessions: list[PcSession], now: datetime) -> dict:
    backing = support(shift.start, shift.end, sessions, now)
    return {"share": round(backing.share, 3), "beforeRecords": backing.before_records,
            "sessions": [{"on": s.on.isoformat(), "off": iso(s.off), "exact": s.exact} for s in backing.sessions]}
