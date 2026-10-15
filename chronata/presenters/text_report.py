from datetime import date, datetime, timedelta

from chronata.presenters.explanation import piece_lines
from chronata.timekeeping.day_entries import DayEntry
from chronata.timekeeping.durations import hours
from chronata.timekeeping.compensation import Reconciliation, all_labels
from chronata.timekeeping.pc_sessions import PcSession
from chronata.timekeeping.stamps import Stamp
from chronata.timekeeping.overtime import Day, Week


def entry_lines(entries: list[DayEntry], sessions: list[PcSession], stamps: list[Stamp], now: datetime) -> list[str]:
    lines = [f"{'date':10}  {'start':8}  {'end':8}  {'worked':>6}  label"]
    for entry in entries:
        end = f"{entry.end:%H:%M:%S}" if entry.end else "--:--:--"
        flags = [entry.label or "(no label)"] + (["OPEN"] if entry.end is None else []) + (["STRUCK OUT"] if entry.voided else [])
        lines.append(f"{entry.start:%Y-%m-%d}  {entry.start:%H:%M:%S}  {end}  {hours(entry.worked(now)):>6}  {', '.join(flags)}")
        for piece in entry.pieces:
            heading, *details = piece_lines(piece, sessions, stamps, now)
            lines.append(f"{'':6}{heading}")
            lines += [f"{'':8}{detail}" for detail in details]
    return lines


def punctuality(day: Day) -> str | None:
    gap = f"{hours(day.short)} behind so far" if day.running else f"{hours(day.short)} short of a full day"
    if day.late <= timedelta():
        return gap if day.short > timedelta() else None
    if day.made_up:
        return f"arrived {hours(day.late)} late, made up so far" if day.running else f"arrived {hours(day.late)} late, made up (left {day.last_out:%H:%M})"
    return f"arrived {hours(day.late)} late, {gap}"


def report_lines(weeks_per_label: dict[str, list[Week]], compensation: dict[str, Reconciliation], today: date) -> list[str]:
    lines = []
    for label, reconciliation in compensation.items():
        lines += [f"{label or '(no label)'}", f"  {'week of':10}  {'worked':>7}  {'overtime':>8}"]
        for week in weeks_per_label.get(label, []):
            running = "  (week still running)" if week.end >= today else ""
            lines.append(f"  {week.start:%Y-%m-%d}  {hours(week.worked):>7}  {hours(week.overtime):>8}{running}")
            lines += [f"    {day.date:%a %d %b}: {note}" for day in week.days if (note := punctuality(day))]
        lines += _compensation_lines(label, reconciliation) + [""]
    everything = all_labels(compensation)
    return lines + [
        "All labels",
        f"  Overtime worked:                  {hours(everything.owed):>8}",
        f"  Compensated (pay or time off):    {hours(everything.compensated):>8}",
        f"  No compensation recorded yet:     {hours(everything.unmatched_overtime):>8}",
        f"  Uncompensated so far:             {hours(everything.shortfall):>8}",
    ]


def _compensation_lines(label: str, reconciliation: Reconciliation) -> list[str]:
    if not reconciliation.periods and not reconciliation.unmatched:
        return []
    lines = ["  Compensation recorded"]
    if not reconciliation.periods:
        lines.append(f"    none yet; add it with: chronata compensation FROM TO HOURS{f' --label {label!r}' if label else ''}")
    for period in reconciliation.periods:
        lines.append(
            f"    {period.start} to {period.end}: overtime worked {hours(period.owed)}, "
            f"paid {hours(period.paid)}, time off {hours(period.time_off)}, "
            f"UNCOMPENSATED {hours(period.shortfall)}"
            + (f"  [{'; '.join(period.references)}]" if period.references else "")
        )
    if reconciliation.unmatched:
        lines.append("  Overtime on days no compensation covers yet")
        lines += [f"    {day.date:%Y-%m-%d %a}: {hours(day.overtime)}" for day in reconciliation.unmatched]
    return lines
