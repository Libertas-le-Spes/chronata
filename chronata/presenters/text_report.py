from datetime import date, datetime, timedelta

from chronata.timekeeping.durations import hours
from chronata.timekeeping.pay import Reconciliation
from chronata.timekeeping.pc_sessions import PcSession, support
from chronata.timekeeping.shifts import Shift
from chronata.timekeeping.stamps import Stamp
from chronata.timekeeping.start_proof import StartProof, start_proof
from chronata.timekeeping.working_day import Day, Week

LATE_ENOUGH_TO_FLAG = timedelta(minutes=15)


def shift_lines(all_shifts: list[Shift], sessions: list[PcSession], stamps: list[Stamp], now: datetime) -> list[str]:
    lines = [f"{'id':>4}  {'date':10}  {'start':8}  {'end':8}  {'worked':>6}  flags"]
    for shift in all_shifts:
        proof = start_proof(shift, sessions, stamps)
        flags = []
        if shift.voided:
            flags.append("STRUCK OUT")
        if shift.end is None:
            flags.append("OPEN")
        if shift.entered_late_by > LATE_ENOUGH_TO_FLAG:
            flags.append("written down later, from the PC-on time" if proof.from_pc_on else f"entered {_ago(shift.entered_late_by)} after the fact")
        end = f"{shift.end:%H:%M:%S}" if shift.end else "--:--:--"
        worked = hours(shift.worked(now)) if shift.end else ""
        if shift.label:
            flags.insert(0, shift.label)
        lines.append(f"{shift.id:>4}  {shift.start:%Y-%m-%d}  {shift.start:%H:%M:%S}  {end}  {worked:>6}  {', '.join(flags)}")
        lines.append(f"{'':>6}start proven by {proven_by(proof, shift.start)}")
        lines.append(f"{'':>6}{pc_support(shift, sessions, now)}")
        lines.extend(f"{'':>6}note: {note}" for note in shift.notes)
        lines.extend(f"{'':>6}{change}" for change in shift.changes)
    return lines


def proven_by(proof: StartProof, start: datetime) -> str:
    source = "PC on" if proof.from_pc_on else f"entry {proof.entry}"
    if not proof.stamps:
        return f"{source} · not yet independently timestamped"
    local = [(stamp.authority_name, stamp.time.astimezone(start.tzinfo)) for stamp in proof.stamps]
    shown = ", ".join(f"{name} {moment:%H:%M:%S}" if moment.date() == start.date() else f"{name} {moment:%Y-%m-%d %H:%M:%S}" for name, moment in local)
    return f"{source} · {shown}"


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
