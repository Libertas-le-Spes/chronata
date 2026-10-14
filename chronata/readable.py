from collections import defaultdict
from datetime import date, datetime, timedelta

from chronata.pc_sessions import PcSession, support
from chronata.report import hours
from chronata.rules import Rules, Week
from chronata.shifts import Shift
from chronata.timestamps import Stamp


def daily_notes(all_shifts: list[Shift], all_weeks: list[Week], sessions: list[PcSession], rules: Rules,
                now: datetime) -> dict[date, str]:
    per_day: dict[date, list[Shift]] = defaultdict(list)
    for shift in all_shifts:
        per_day[shift.start.date()].append(shift)
    overtime = {day.date: day.overtime for week in all_weeks for day in week.days}
    return {
        day: _day(day, shifts, overtime.get(day), sessions, rules, now)
        for day, shifts in sorted(per_day.items())
    }


def overview(stamps: list[Stamp], entries: int) -> str:
    return f"# Chronata\n\n{_seal(stamps, entries)}\n\nThe sealed record is in the `sealed` folder. Check it with `chronata verify --folder <this folder>`.\n"


def text_log(notes: dict[date, str], stamps: list[Stamp], entries: int) -> str:
    return f"CHRONATA TIME LOG\n{_seal(stamps, entries)}\n\n" + "\n\n".join(notes.values())


def _day(day: date, shifts: list[Shift], overtime, sessions: list[PcSession], rules: Rules, now: datetime) -> str:
    counted = [s for s in shifts if s.end and not s.voided]
    worked = sum((rules.worked(s.start, s.end) for s in counted), timedelta())
    lunch = sum((rules.lunch_overlap(s.start, s.end) for s in counted), timedelta())
    lines = [
        f"# {day:%A %d %B %Y}",
        "",
        f"Worked {hours(worked)} · overtime {hours(overtime) if overtime is not None else '0:00'} · lunch taken off {hours(lunch)}",
        "",
        "| In | Out | Worked | PC on | |",
        "|---|---|---|---|---|",
    ]
    for shift in shifts:
        backing = support(shift.start, shift.end, sessions, now)
        pc = "no record" if not backing.sessions else f"{backing.share:.0%}"
        state = "struck out" if shift.voided else ("open" if shift.end is None else "")
        end = f"{shift.end:%H:%M:%S}" if shift.end else "–"
        worked_here = hours(rules.worked(shift.start, shift.end)) if shift.end else "–"
        lines.append(f"| {shift.start:%H:%M:%S} | {end} | {worked_here} | {pc} | {state} |")
    for shift in shifts:
        lines += [f"- Note ({shift.start:%H:%M}): {note}" for note in shift.notes]
        lines += [f"- Change ({shift.start:%H:%M}): {change}" for change in shift.changes]
    return "\n".join(lines) + "\n"


def _seal(stamps: list[Stamp], entries: int) -> str:
    if not stamps:
        return f"{entries} sealed entries, not yet independently timestamped."
    latest = max(s.seq for s in stamps)
    by = ", ".join(f"{s.authority_name} at {s.time:%Y-%m-%d %H:%M:%S} UTC" for s in stamps if s.seq == latest)
    return f"{entries} sealed entries. Everything up to entry {latest} was independently timestamped by {by}."
