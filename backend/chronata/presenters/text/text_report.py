from datetime import date, datetime

from chronata.presenters.day.day_story import DayRecords, Line, day_story
from chronata.timekeeping.compensation.compensation import all_labels
from chronata.timekeeping.compensation.lateness_offset import LatenessOffset
from chronata.timekeeping.compensation.period import Period
from chronata.timekeeping.compensation.reconciliation import Reconciliation
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.week import Week
from chronata.timekeeping.pc.pc_sessions import PcSession
from chronata.timekeeping.record.stamps import Stamp
from chronata.timekeeping.shifts.day_entries import DayEntry, pc_share
from chronata.timekeeping.shifts.durations import NONE
from chronata.timekeeping.shifts.durations import hours
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
        lines += _compensation_lines(label, reconciliation)
        lines += _lateness_lines(reconciliation.lateness) + [""]
    everything = all_labels(compensation)
    return lines + [
        "All labels",
        f"  Overtime worked:                  {hours(everything.owed.earned):>8}",
        f"  Compensated (pay or time off):    {hours(everything.compensated):>8}",
        f"  No compensation recorded yet:     {hours(everything.unmatched_overtime.earned):>8}",
        f"  Uncompensated so far:             {hours(everything.shortfall):>8}",
        f"  Lateness not covered:             {hours(-everything.lateness_offset):>8}",
        f"  Uncompensated after lateness:     {hours(everything.uncompensated):>8}",
    ]


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


def _lateness_lines(lateness: list[LatenessOffset]) -> list[str]:
    if not lateness:
        return []
    lines = ["  Lateness not covered that day, taken off the uncompensated total"]
    for offset in lateness:
        lines.append(f"    {offset.date:%a %d %b}: {hours(offset.late)}")
    return lines


def _compensation_lines(label: str, reconciliation: Reconciliation) -> list[str]:
    if not reconciliation.periods and not reconciliation.unmatched:
        return []
    return ["  Compensation recorded", *_recorded(label, reconciliation.periods), *_not_covered(reconciliation.unmatched)]


def _recorded(label: str, periods: list[Period]) -> list[str]:
    if not periods:
        return [f"    none yet; add it with: chronata compensation FROM TO HOURS{f' --label {label!r}' if label else ''}"]
    return [_period_line(period) for period in periods]


def _period_line(period: Period) -> str:
    return (f"    {period.start} to {period.end}: overtime worked {hours(period.owed.earned)}, paid {hours(period.paid)}, "
            f"time off {hours(period.time_off)}, UNCOMPENSATED {hours(period.shortfall)}{_references(period)}")


def _references(period: Period) -> str:
    if not period.references:
        return ""
    return f"  [{'; '.join(period.references)}]"


def _not_covered(unmatched: list[Day]) -> list[str]:
    if not unmatched:
        return []
    lines = ["  Overtime on days no compensation covers yet"]
    for day in unmatched:
        lines.append(f"    {day.date:%Y-%m-%d %a}: {hours(day.overtime.earned)}")
    return lines
