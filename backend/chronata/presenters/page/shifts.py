from datetime import datetime

from chronata.presenters.day.day_story import LATE_ENOUGH_TO_FLAG, DayRecords, Line, day_story
from chronata.presenters.page.facts import PageFacts
from chronata.presenters.page.values import iso
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.timesheet import days_so_far
from chronata.timekeeping.hours.week import Week
from chronata.timekeeping.pc.pc_sessions import PcSession, support
from chronata.timekeeping.pc.start_proof import start_proof
from chronata.timekeeping.record.stamps import Stamp
from chronata.timekeeping.shifts.day_entries import DayEntry, day_entries, pc_share
from chronata.timekeeping.shifts.durations import minutes
from chronata.timekeeping.shifts.shifts import Shift


def state(facts: PageFacts) -> dict:
    return {
        "weeks": [_week(week, facts.now) for week in reversed(facts.weeks)],
        "entries": _entries(facts),
        "unexplainedBreaks": _unexplained_breaks(facts.shifts),
    }


def _week(week: Week, now: datetime) -> dict:
    return {"start": week.start.isoformat(), "end": week.end.isoformat(), "worked": minutes(week.worked),
            "overtime": minutes(week.overtime.earned), "running": week.end >= now.date()}


def _entries(facts: PageFacts) -> list[dict]:
    days = days_so_far(facts.shifts, facts.hours, facts.now)
    records = DayRecords(facts.sessions, facts.stamps, facts.now)
    shown = []
    for entry in sorted(day_entries(facts.shifts), key=_newest_day_first):
        shown.append(_entry(entry, days.get((entry.day, facts.hours.counted_under(entry.label))), records))
    return shown


def _newest_day_first(entry: DayEntry) -> tuple[int, datetime]:
    return -entry.day.toordinal(), entry.start


def _unexplained_breaks(all_shifts: list[Shift]) -> list[dict]:
    found = []
    for shift in all_shifts:
        for gap in shift.breaks:
            if gap.unexplained_pc_off:
                found.append({"shift": shift.id, "start": gap.start.isoformat(), "end": gap.end.isoformat()})
    return found


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
        "waivers": _waivers(entry),
        "lines": [_line(line, entry) for line in day_story(entry, records)],
        "pieces": [_piece(piece, sessions, stamps, now) for piece in entry.pieces],
    }


def _waivers(entry: DayEntry) -> list[dict]:
    found = []
    for piece in entry.counted:
        for gap in piece.breaks:
            if gap.waived:
                found.append({"shift": piece.id, "start": gap.start.isoformat(), "end": gap.end.isoformat(),
                              "minutes": minutes(gap.end - gap.start), "reason": gap.reason})
    return found


def _line(line: Line, entry: DayEntry) -> dict:
    return {"what": line.what, "time": line.time_on(entry.day), "detail": line.detail, "mistake": line.mistake}


def _punctuality(day: Day | None) -> dict | None:
    if day is None or not day.punctuality.worth_noting:
        return None
    punctuality = day.punctuality
    return {"late": minutes(punctuality.late), "short": minutes(punctuality.short), "madeUp": punctuality.made_up, "running": day.running,
            "lastOut": day.last_out.isoformat(), "afterShift": punctuality.started_after_shift}


def _piece(shift: Shift, sessions: list[PcSession], stamps: list[Stamp], now: datetime) -> dict:
    return {
        "lateBy": minutes(shift.entered_late_by) if shift.entered_late_by > LATE_ENOUGH_TO_FLAG else None,
        "voided": shift.voided,
        "corrections": len(shift.corrections),
        "fromPcOn": start_proof(shift, sessions, stamps).from_pc_on,
        "beforeRecords": support(shift.start, shift.end, sessions, now).before_records,
    }
