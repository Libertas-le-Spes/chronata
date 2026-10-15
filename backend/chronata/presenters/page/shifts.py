from datetime import datetime

from chronata.presenters.page.day_lines import DayRecords, day_lines
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
        "entries": [_entry(entry, days.get((entry.day, entry.label or facts.hours.default_label)), DayRecords(facts.sessions, stamps, facts.now))
                    for entry in newest_day_first],
        "unexplainedBreaks": [
            {"shift": shift.id, "start": gap.start.isoformat(), "end": gap.end.isoformat()}
            for shift in facts.shifts for gap in shift.breaks if gap.unexplained_pc_off
        ],
    }


def _entry(entry: DayEntry, day: Day | None, records: DayRecords) -> dict:
    sessions, stamps, now = records.sessions, records.stamps, records.now
    return {
        "day": entry.day.isoformat(),
        "label": entry.label,
        "start": entry.start.isoformat(),
        "end": iso(entry.end),
        "worked": minutes(entry.worked(now)),
        "voided": entry.voided,
        "pcShare": pc_share(entry, sessions, now),
        "punctuality": _punctuality(day),
        "ids": [piece.id for piece in entry.counted],
        "lines": day_lines(entry, records),
        "pieces": [_piece(piece, sessions, stamps, now) for piece in entry.pieces],
    }


def _punctuality(day: Day | None) -> dict | None:
    if day is None or not day.worth_noting:
        return None
    return {"late": minutes(day.late), "short": minutes(day.short), "madeUp": day.made_up, "running": day.running, "lastOut": day.last_out.isoformat()}


def _piece(shift: Shift, sessions: list[PcSession], stamps: list[Stamp], now: datetime) -> dict:
    return {
        "lateBy": minutes(shift.entered_late_by) if shift.entered_late_by > LATE_ENOUGH_TO_FLAG else None,
        "voided": shift.voided,
        "corrections": len(shift.corrections),
        "fromPcOn": start_proof(shift, sessions, stamps).from_pc_on,
        "beforeRecords": support(shift.start, shift.end, sessions, now).before_records,
    }
