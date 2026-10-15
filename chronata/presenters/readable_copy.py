import re
from collections import defaultdict
from datetime import date, datetime, timedelta

from chronata.presenters.explanation import piece_lines
from chronata.presenters.text_report import punctuality
from chronata.timekeeping.durations import hours
from chronata.timekeeping.day_entries import DayEntry, day_entries, pc_share
from chronata.timekeeping.pc_sessions import PcSession
from chronata.timekeeping.shifts import Shift, completed
from chronata.timekeeping.stamps import Stamp, latest
from chronata.timekeeping.label_hours import LabelHours
from chronata.timekeeping.overtime import Day, Week, combined, days_so_far, weeks_by_label

OVERVIEW = "README.md"
WHOLE_LOG = "Chronata time log.md"
DAYS = "Days"
NO_LABEL = "No label"


def label_folder(label: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "-", label).strip(" .-")
    return cleaned or NO_LABEL


def readable_files(all_shifts: list[Shift], label_hours: LabelHours, sessions: list[PcSession],
                   stamps: list[Stamp], entries: int, now: datetime) -> dict[str, bytes]:
    summaries = days_so_far(all_shifts, label_hours, now)
    all_weeks = combined(weeks_by_label(completed(all_shifts), label_hours), label_hours.default_label)
    by_folder: dict[str, list[Shift]] = defaultdict(list)
    for shift in all_shifts:
        by_folder[label_folder(shift.label)].append(shift)
    files: dict[str, bytes] = {}
    totals: dict[str, timedelta] = {}
    for folder, shifts in sorted(by_folder.items()):
        days = _day_notes(folder, shifts, summaries, label_hours.default_label, sessions, stamps, now)
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


def _day_notes(folder: str, shifts: list[Shift], summaries: dict[tuple[date, str], Day], default_label: str, sessions: list[PcSession],
               stamps: list[Stamp], now: datetime) -> dict[date, str]:
    per_day: dict[date, list[DayEntry]] = defaultdict(list)
    for entry in day_entries(shifts):
        per_day[entry.day].append(entry)
    return {day: _day(folder, day, entries, summaries.get((day, entries[0].label or default_label)), sessions, stamps, now)
            for day, entries in sorted(per_day.items())}


def _day(folder: str, day: date, entries: list[DayEntry], summary: Day | None, sessions: list[PcSession], stamps: list[Stamp], now: datetime) -> str:
    worked = sum((entry.worked(now) for entry in entries), timedelta())
    running = " so far" if any(entry.end is None for entry in entries) else ""
    note = punctuality(summary) if summary else None
    overtime = f", overtime {hours(summary.overtime)}" if summary and summary.overtime else ""
    lines = [f"# {day:%A %d %B %Y}", "", f"{folder}: worked {hours(worked)}{running}{overtime}" + (f", {note}" if note else ""), ""]
    lines += ["| In | Out | Worked | PC on | Status |", "|---|---|---|---|---|"]
    for entry in entries:
        share = pc_share(entry, sessions, now)
        status = "struck out" if entry.voided else ("still open" if entry.end is None else "")
        end = f"{entry.end:%H:%M:%S}" if entry.end else "–"
        worked_here = hours(entry.worked(now)) + ("" if entry.end else " so far")
        lines.append(f"| {entry.start:%H:%M:%S} | {end} | {worked_here} | {'no record' if share is None else f'{share:.0%}'} | {status} |")
    lines += ["", "## Full explanation", ""]
    for entry in entries:
        for piece in entry.pieces:
            heading, *details = piece_lines(piece, sessions, stamps, now)
            lines += [f"- {heading}", *(f"  - {detail}" for detail in details)]
    return "\n".join(lines) + "\n"


def _seal(stamps: list[Stamp], entries: int) -> str:
    newest, by = latest(stamps)
    if newest is None:
        return f"{entries} sealed entries, not yet independently timestamped."
    names = ", ".join(f"{s.authority_name} at {s.time:%Y-%m-%d %H:%M:%S} UTC" for s in by)
    return f"{entries} sealed entries. Everything up to entry {newest} was independently timestamped by {names}."
