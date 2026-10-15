from datetime import date, datetime, timedelta

from chronata.presenters.explanation import piece_lines
from chronata.timekeeping.day_entries import DayEntry
from chronata.timekeeping.durations import hours
from chronata.timekeeping.pay import Reconciliation
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
    if day.late <= timedelta():
        return f"{hours(day.short)} short of a full day" if day.short > timedelta() else None
    if day.made_up:
        return f"arrived {hours(day.late)} late, made up (left {day.last_out:%H:%M})"
    return f"arrived {hours(day.late)} late, {hours(day.short)} short of a full day"


def report_lines(all_weeks: list[Week], reconciliation: Reconciliation, today: date, by_label: dict[str, timedelta]) -> list[str]:
    lines = ["Weeks worked", f"  {'week of':10}  {'worked':>7}  {'overtime':>8}"]
    for week in all_weeks:
        running = "  (week still running)" if week.end >= today else ""
        lines.append(f"  {week.start:%Y-%m-%d}  {hours(week.worked):>7}  {hours(week.overtime):>8}{running}")
        lines += [f"    {day.date:%a %d %b}: {note}" for day in week.days if (note := punctuality(day))]

    if any(by_label):
        lines += ["", "By label"]
        lines += [f"  {label or '(no label)':24} {hours(worked):>8}" for label, worked in by_label.items()]

    lines += ["", "Pay periods you recorded from payslips"]
    if not reconciliation.periods:
        lines.append("  none yet; add one with: chronata paid FROM TO HOURS")
    for period in reconciliation.periods:
        lines.append(
            f"  {period.start} to {period.end}: overtime worked {hours(period.owed)}, "
            f"paid {hours(period.paid)}, time off {hours(period.time_off)}, "
            f"UNCOMPENSATED {hours(period.shortfall)}"
            + (f"  [{'; '.join(period.references)}]" if period.references else "")
        )

    if reconciliation.unmatched:
        lines += ["", "Overtime on days no payslip covers yet"]
        lines += [f"  {day.date:%Y-%m-%d %a}: {hours(day.overtime)}" for day in reconciliation.unmatched]

    lines += [
        "",
        f"Overtime worked:            {hours(reconciliation.owed):>8}",
        f"Compensated (pay or leave): {hours(reconciliation.compensated):>8}",
        f"Not yet matched to payslip: {hours(reconciliation.unmatched_overtime):>8}",
        f"Uncompensated so far:       {hours(reconciliation.shortfall):>8}",
    ]
    return lines
