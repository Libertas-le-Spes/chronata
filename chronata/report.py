from datetime import date, datetime, timedelta

from chronata.compensation import Reconciliation
from chronata.pc_sessions import PcSession, support
from chronata.rules import Rules, Week
from chronata.shifts import Shift

LATE_ENOUGH_TO_FLAG = timedelta(minutes=15)


def hours(span: timedelta) -> str:
    minutes = round(span.total_seconds() / 60)
    return f"{minutes // 60}:{minutes % 60:02d}"


def shift_lines(all_shifts: list[Shift], sessions: list[PcSession], rules: Rules, now: datetime) -> list[str]:
    lines = [f"{'id':>4}  {'date':10}  {'start':8}  {'end':8}  {'worked':>6}  flags"]
    for shift in all_shifts:
        flags = []
        if shift.voided:
            flags.append("STRUCK OUT")
        if shift.end is None:
            flags.append("OPEN")
        if shift.entered_late_by > LATE_ENOUGH_TO_FLAG:
            flags.append(f"entered {_ago(shift.entered_late_by)} after the fact")
        end = f"{shift.end:%H:%M:%S}" if shift.end else "--:--:--"
        worked = hours(rules.worked(shift.start, shift.end)) if shift.end else ""
        lunch = rules.lunch_overlap(shift.start, shift.end or now)
        if lunch:
            flags.append(f"lunch -{hours(lunch)}")
        lines.append(f"{shift.id:>4}  {shift.start:%Y-%m-%d}  {shift.start:%H:%M:%S}  {end}  {worked:>6}  {', '.join(flags)}")
        lines.append(f"{'':>6}{pc_support(shift, sessions, now)}")
        lines.extend(f"{'':>6}note: {note}" for note in shift.notes)
        lines.extend(f"{'':>6}{change}" for change in shift.changes)
    return lines


def report_lines(all_weeks: list[Week], reconciliation: Reconciliation, today: date) -> list[str]:
    lines = ["Weeks worked", f"  {'week of':10}  {'worked':>7}  {'overtime':>8}"]
    for week in all_weeks:
        running = "  (week still running)" if week.end >= today else ""
        lines.append(f"  {week.start:%Y-%m-%d}  {hours(week.worked):>7}  {hours(week.overtime):>8}{running}")

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


def pc_support(shift: Shift, sessions: list[PcSession], now: datetime) -> str:
    backing = support(shift.start, shift.end, sessions, now)
    if not backing.sessions:
        return "PC: no record (before PC records begin)" if backing.before_records else "PC: off for the whole shift"
    spans = ", ".join(f"{s.on:%a %H:%M}–{_off(s)}" for s in backing.sessions)
    return f"PC: on for {backing.share:.0%} of the shift ({spans})"


def _off(session: PcSession) -> str:
    if session.off is None:
        return "still on"
    return f"{session.off:%a %H:%M:%S} shutdown" if session.exact else f"{session.off:%a %H:%M} last activity"


def _ago(span: timedelta) -> str:
    if span >= timedelta(days=1):
        return f"{span.days}d {span.seconds // 3600}h"
    return hours(span) + "h"
