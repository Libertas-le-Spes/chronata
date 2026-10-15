import re
from collections import defaultdict
from datetime import date, datetime, timedelta

from chronata.presenters.text_report import proven_by, punctuality
from chronata.timekeeping.durations import hours
from chronata.timekeeping.pc_sessions import PcSession, support
from chronata.timekeeping.shifts import Shift
from chronata.timekeeping.stamps import Stamp, latest
from chronata.timekeeping.start_proof import start_proof
from chronata.timekeeping.working_day import Day, Week

OVERVIEW = "README.md"
WHOLE_LOG = "Chronata time log.md"
DAYS = "Days"
NO_LABEL = "No label"


def label_folder(label: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "-", label).strip(" .-")
    return cleaned or NO_LABEL


def readable_files(all_shifts: list[Shift], all_weeks: list[Week], sessions: list[PcSession],
                   stamps: list[Stamp], entries: int, now: datetime) -> dict[str, bytes]:
    summaries = {day.date: day for week in all_weeks for day in week.days}
    by_folder: dict[str, list[Shift]] = defaultdict(list)
    for shift in all_shifts:
        by_folder[label_folder(shift.label)].append(shift)
    files: dict[str, bytes] = {}
    totals: dict[str, timedelta] = {}
    for folder, shifts in sorted(by_folder.items()):
        days = _day_notes(folder, shifts, summaries, sessions, stamps, now)
        totals[folder] = sum((s.worked(s.end or now) for s in shifts if not s.voided), timedelta())
        files.update({f"{folder}/{DAYS}/{day:%Y-%m-%d}.md": note.encode() for day, note in days.items()})
        files[f"{folder}/{OVERVIEW}"] = _label_overview(folder, days, totals[folder], stamps, entries).encode()
        files[f"{folder}/{WHOLE_LOG}"] = _whole_log(folder, days, stamps, entries).encode()
    files[OVERVIEW] = _overview(all_weeks, totals, stamps, entries).encode()
    return files


def _overview(all_weeks: list[Week], totals: dict[str, timedelta], stamps: list[Stamp], entries: int) -> str:
    lines = ["# Chronata time log", "", _seal(stamps, entries), "", "## Labels", ""]
    lines += [f"- [{folder}](<{folder}/{OVERVIEW}>): {hours(worked)} worked" for folder, worked in totals.items()]
    if not totals:
        lines.append("Nothing logged yet.")
    lines += ["", "## Recent weeks, all labels", ""]
    if all_weeks:
        lines += ["| Week of | Worked | Overtime |", "|---|---|---|"]
        lines += [f"| {week.start:%d %b %Y} | {hours(week.worked)} | {hours(week.overtime)} |" for week in reversed(all_weeks[-8:])]
    else:
        lines.append("No finished shifts yet.")
    lines += ["", "The sealed record covers every label: `ledger.jsonl` with its `timestamps` (inside `sealed/` in saved copies). "
              "Check any copy with `chronata verify --folder <this folder>`."]
    return "\n".join(lines) + "\n"


def _label_overview(folder: str, days: dict[date, str], worked: timedelta, stamps: list[Stamp], entries: int) -> str:
    lines = [f"# {folder}", "", f"{hours(worked)} worked in total.", "", _seal(stamps, entries), "", "## Days", ""]
    lines += [f"- [{day:%A %d %B %Y}]({DAYS}/{day:%Y-%m-%d}.md)" for day in sorted(days, reverse=True)]
    lines += ["", f"Everything for {folder} is also in one file: [{WHOLE_LOG}](<{WHOLE_LOG}>)."]
    return "\n".join(lines) + "\n"


def _whole_log(folder: str, days: dict[date, str], stamps: list[Stamp], entries: int) -> str:
    notes = [note.replace("# ", "## ", 1) for _, note in sorted(days.items(), reverse=True)]
    return f"# {folder}: time log\n\n{_seal(stamps, entries)}\n\n" + "\n".join(notes)


def _day_notes(folder: str, shifts: list[Shift], summaries: dict[date, Day], sessions: list[PcSession],
               stamps: list[Stamp], now: datetime) -> dict[date, str]:
    per_day: dict[date, list[Shift]] = defaultdict(list)
    for shift in shifts:
        per_day[shift.start.date()].append(shift)
    return {day: _day(folder, day, sorted(day_shifts, key=lambda s: s.start), summaries.get(day), sessions, stamps, now)
            for day, day_shifts in sorted(per_day.items())}


def _day(folder: str, day: date, shifts: list[Shift], summary: Day | None, sessions: list[PcSession], stamps: list[Stamp], now: datetime) -> str:
    counted = [s for s in shifts if not s.voided]
    worked = sum((s.worked(s.end or now) for s in counted), timedelta())
    running = " so far" if any(s.end is None for s in counted) else ""
    whole_day = ""
    if summary:
        note = punctuality(summary)
        whole_day = f"Whole day, all labels: worked {hours(summary.worked)}, overtime {hours(summary.overtime)}" + (f", {note}" if note else "")
    lines = [f"# {day:%A %d %B %Y}", "", f"{folder}: worked {hours(worked)}{running}", ""]
    if whole_day:
        lines += [whole_day, ""]
    lines += ["| In | Start proven by | Out | Worked | PC on | Status |", "|---|---|---|---|---|---|"]
    for shift in shifts:
        backing = support(shift.start, shift.end, sessions, now)
        pc = "no record" if not backing.sessions else f"{backing.share:.0%}"
        status = "struck out" if shift.voided else ("still open" if shift.end is None else "")
        end = f"{shift.end:%H:%M:%S}" if shift.end else "–"
        worked_here = hours(shift.worked(shift.end or now)) + ("" if shift.end else " so far")
        proof = proven_by(start_proof(shift, sessions, stamps), shift.start)
        lines.append(f"| {shift.start:%H:%M:%S} | {proof} | {end} | {worked_here} | {pc} | {status} |")
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
