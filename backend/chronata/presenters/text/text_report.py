from datetime import date, datetime

from chronata.presenters.day.day_story import DayRecords, Line, day_story
from chronata.presenters.text.compensation_lines import label_compensation, totals
from chronata.timekeeping.compensation.reconciliation import Reconciliation
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.week import Week
from chronata.timekeeping.pc.pc_sessions import PcSession
from chronata.timekeeping.record.stamps import Stamp
from chronata.timekeeping.shifts.day_entries import DayEntry, pc_share
from chronata.timekeeping.shifts.durations import NONE, hours
from chronata.timekeeping.shifts.shifts import named


def entry_lines(entries: list[DayEntry], sessions: list[PcSession], stamps: list[Stamp], now: datetime) -> list[str]:
    records = DayRecords(sessions, stamps, now)
    lines = [f"{'date':10}  {'start':8}  {'end':8}  {'worked':>6}  label"]
    for entry in entries:
        end = f"{entry.end:%H:%M:%S}" if entry.end else "--:--:--"
        lines.append(f"{entry.start:%Y-%m-%d}  {entry.start:%H:%M:%S}  {end}  {hours(entry.worked(now)):>6}  {', '.join(_flags(entry, records))}")
        lines += [_story_line(line, entry) for line in day_story(entry, records)]
    return lines


def _flags(entry: DayEntry, records: DayRecords) -> list[str]:
    share = pc_share(entry, records.sessions, records.now)
    pc = [f"PC on {share:.0%}"] if share is not None and not entry.voided else []
    status = ["OPEN"] * (entry.end is None) + ["MARKED AS A MISTAKE"] * entry.voided
    return [entry.label or "(no label)", *status, *pc, named(sorted(entry.pieces, key=lambda piece: piece.id))]


def _story_line(line: Line, entry: DayEntry) -> str:
    own = f" (shift {line.mistake})" if line.mistake else ""
    return f"{'':6}{line.what:<20}{line.time_on(entry.day):<18}{line.detail}{own}".rstrip()


def punctuality(day: Day) -> str | None:
    punctuality = day.punctuality
    if punctuality.started_after_shift:
        return "started after the shift ended, so not counted as late; check this day"
    if punctuality.arrived_late:
        return f"arrived {hours(punctuality.late)} late, {_after_arriving_late(day)}"
    if punctuality.short > NONE:
        return _behind(day)
    return None


def _after_arriving_late(day: Day) -> str:
    if day.punctuality.made_up:
        return _made_up(day)
    return _behind(day)


def _behind(day: Day) -> str:
    short = hours(day.punctuality.short)
    if day.running:
        return f"{short} behind so far"
    return f"{short} short of a full day"


def _made_up(day: Day) -> str:
    if day.running:
        return "made up so far"
    return f"made up (left {day.last_out:%H:%M})"


def report_lines(weeks_per_label: dict[str, list[Week]], compensation: dict[str, Reconciliation], today: date) -> list[str]:
    lines = []
    for label, reconciliation in compensation.items():
        lines += [_label_heading(label), f"  {'week of':10}  {'worked':>7}  {'overtime':>8}"]
        for week in weeks_per_label.get(label, []):
            lines.append(f"  {week.start:%Y-%m-%d}  {hours(week.worked):>7}  {hours(week.overtime.earned):>8}{_still_running(week, today)}")
            lines += _punctuality_lines(week)
        lines += label_compensation(label, reconciliation) + [""]
    return lines + totals(compensation)


def _label_heading(label: str) -> str:
    if label:
        return label
    return "(no label)"


def _still_running(week: Week, today: date) -> str:
    if week.end >= today:
        return "  (week still running)"
    return ""


def _punctuality_lines(week: Week) -> list[str]:
    lines = []
    for day in week.days:
        note = punctuality(day)
        if note:
            lines.append(f"    {day.date:%a %d %b}: {note}")
    return lines
