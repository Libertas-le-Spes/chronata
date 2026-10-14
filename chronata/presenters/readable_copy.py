from collections import defaultdict
from datetime import date, datetime, timedelta

from chronata.presenters.text_report import punctuality
from chronata.timekeeping.durations import hours
from chronata.timekeeping.pc_sessions import PcSession, support
from chronata.timekeeping.shifts import Shift
from chronata.timekeeping.stamps import Stamp, latest
from chronata.timekeeping.working_day import Day, Week

OVERVIEW = "README.md"
WHOLE_LOG = "Chronata time log.md"
DAYS = "Days"


def readable_files(all_shifts: list[Shift], all_weeks: list[Week], sessions: list[PcSession],
                   stamps: list[Stamp], entries: int, now: datetime) -> dict[str, bytes]:
    days = _day_notes(all_shifts, all_weeks, sessions, now)
    files = {f"{DAYS}/{day:%Y-%m-%d}.md": note.encode() for day, note in days.items()}
    files[OVERVIEW] = _overview(all_weeks, days, stamps, entries).encode()
    files[WHOLE_LOG] = _whole_log(days, stamps, entries).encode()
    return files


def _overview(all_weeks: list[Week], days: dict[date, str], stamps: list[Stamp], entries: int) -> str:
    lines = ["# Chronata time log", "", _seal(stamps, entries), "", "## Recent weeks", "", "| Week of | Worked | Overtime |", "|---|---|---|"]
    lines += [f"| {week.start:%d %b %Y} | {hours(week.worked)} | {hours(week.overtime)} |" for week in reversed(all_weeks[-8:])]
    if not all_weeks:
        lines[-2:] = ["No finished shifts yet."]
    lines += ["", "## Days", ""]
    lines += [f"- [{day:%A %d %B %Y}]({DAYS}/{day:%Y-%m-%d}.md)" for day in sorted(days, reverse=True)]
    lines += ["", f"Everything is also in one file: [{WHOLE_LOG}](<{WHOLE_LOG}>).",
              "", "The sealed record is `ledger.jsonl` with its `timestamps` (inside `sealed/` in saved copies). "
              "Check any copy with `chronata verify --folder <this folder>`."]
    return "\n".join(lines) + "\n"


def _whole_log(days: dict[date, str], stamps: list[Stamp], entries: int) -> str:
    notes = [note.replace("# ", "## ", 1) for _, note in sorted(days.items(), reverse=True)]
    return f"# Chronata time log\n\n{_seal(stamps, entries)}\n\n" + "\n".join(notes)


def _day_notes(all_shifts: list[Shift], all_weeks: list[Week], sessions: list[PcSession], now: datetime) -> dict[date, str]:
    per_day: dict[date, list[Shift]] = defaultdict(list)
    for shift in all_shifts:
        per_day[shift.start.date()].append(shift)
    summaries = {day.date: day for week in all_weeks for day in week.days}
    return {day: _day(day, shifts, summaries.get(day), sessions, now) for day, shifts in sorted(per_day.items())}


def _day(day: date, shifts: list[Shift], summary: Day | None, sessions: list[PcSession], now: datetime) -> str:
    counted = [s for s in shifts if not s.voided]
    worked = sum((s.worked(s.end or now) for s in counted), timedelta())
    running = " so far" if any(s.end is None for s in counted) else ""
    lines = [
        f"# {day:%A %d %B %Y}",
        "",
        f"Worked {hours(worked)}{running} · overtime {hours(summary.overtime) if summary else '0:00'}"
        + (f" · {note}" if summary and (note := punctuality(summary)) else ""),
        "",
        "| In | Out | Worked | Label | PC on | Status |",
        "|---|---|---|---|---|---|",
    ]
    for shift in shifts:
        backing = support(shift.start, shift.end, sessions, now)
        pc = "no record" if not backing.sessions else f"{backing.share:.0%}"
        status = "struck out" if shift.voided else ("still open" if shift.end is None else "")
        end = f"{shift.end:%H:%M:%S}" if shift.end else "–"
        worked_here = hours(shift.worked(shift.end or now)) + ("" if shift.end else " so far")
        lines.append(f"| {shift.start:%H:%M:%S} | {end} | {worked_here} | {shift.label} | {pc} | {status} |")
    for shift in shifts:
        lines += [f"- Note ({shift.start:%H:%M}): {note}" for note in shift.notes]
        lines += [f"- Change ({shift.start:%H:%M}): {change}" for change in shift.changes]
    return "\n".join(lines) + "\n"


def _seal(stamps: list[Stamp], entries: int) -> str:
    newest, by = latest(stamps)
    if newest is None:
        return f"{entries} sealed entries, not yet independently timestamped."
    names = ", ".join(f"{s.authority_name} at {s.time:%Y-%m-%d %H:%M:%S} UTC" for s in by)
    return f"{entries} sealed entries. Everything up to entry {newest} was independently timestamped by {names}."
