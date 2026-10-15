from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from chronata.timekeeping.shifts import Shift, completed, open_shift
from chronata.timekeeping.label_hours import LabelHours
from chronata.timekeeping.working_day import WorkingDay

NONE = timedelta()


@dataclass(frozen=True)
class Day:
    date: date
    worked: timedelta
    overtime: timedelta
    first_in: datetime
    last_out: datetime
    late: timedelta
    short: timedelta

    @property
    def made_up(self) -> bool:
        return self.late > NONE and self.short == NONE


@dataclass(frozen=True)
class Week:
    start: date
    days: tuple[Day, ...]

    @property
    def end(self) -> date:
        return self.start + timedelta(days=6)

    @property
    def worked(self) -> timedelta:
        return sum((day.worked for day in self.days), NONE)

    @property
    def overtime(self) -> timedelta:
        return sum((day.overtime for day in self.days), NONE)


def weeks(finished_shifts: list[Shift], working_day: WorkingDay | None, running: date | None = None) -> list[Week]:
    per_day: dict[date, list[Shift]] = defaultdict(list)
    for shift in finished_shifts:
        per_day[shift.start.date()].append(shift)
    per_week: dict[date, list[tuple[date, list[Shift]]]] = defaultdict(list)
    for day, day_shifts in sorted(per_day.items()):
        per_week[day - timedelta(days=day.weekday())].append((day, day_shifts))
    return [Week(start, _days(worked_days, working_day, running)) for start, worked_days in sorted(per_week.items())]


def weeks_by_label(finished_shifts: list[Shift], hours: LabelHours, running: date | None = None) -> dict[str, list[Week]]:
    grouped: dict[str, list[Shift]] = defaultdict(list)
    for shift in finished_shifts:
        grouped[shift.label or hours.default_label].append(shift)
    return {label: weeks(label_shifts, hours.for_label(label), running) for label, label_shifts in grouped.items()}


def days_so_far(all_shifts: list[Shift], hours: LabelHours, now: datetime) -> dict[tuple[date, str], Day]:
    running = open_shift(all_shifts)
    counted = completed(all_shifts) + ([replace(running, end=now)] if running else [])
    by_label = weeks_by_label(counted, hours, running.start.date() if running else None)
    return {(day.date, label): day for label, label_weeks in by_label.items() for week in label_weeks for day in week.days}


def combined(by_label: dict[str, list[Week]], main_label: str) -> list[Week]:
    per_day: dict[date, list[tuple[str, Day]]] = defaultdict(list)
    for label, label_weeks in by_label.items():
        for week in label_weeks:
            for day in week.days:
                per_day[day.date].append((label, day))
    merged: dict[date, list[Day]] = defaultdict(list)
    for day, found in sorted(per_day.items()):
        main = next((d for label, d in found if label == main_label), None)
        merged[day - timedelta(days=day.weekday())].append(Day(
            day,
            sum((d.worked for _, d in found), NONE),
            sum((d.overtime for _, d in found), NONE),
            min(d.first_in for _, d in found),
            max(d.last_out for _, d in found),
            main.late if main else NONE,
            main.short if main else NONE,
        ))
    return [Week(start, tuple(days)) for start, days in sorted(merged.items())]


def _days(worked_days: list[tuple[date, list[Shift]]], working_day: WorkingDay | None, running: date | None) -> tuple[Day, ...]:
    if working_day is None:
        return tuple(_unmeasured(day, day_shifts) for day, day_shifts in worked_days)
    full_day = timedelta(hours=working_day.daily_hours)
    weekly_room = timedelta(hours=working_day.weekly_hours)
    days = []
    for day, day_shifts in worked_days:
        worked = sum((shift.worked(shift.end) for shift in day_shifts), NONE)
        workday = day.weekday() in working_day.workdays
        ordinary = min(worked, full_day, weekly_room) if workday else NONE
        weekly_room -= ordinary
        first_in = min(shift.start for shift in day_shifts)
        last_out = max(shift.end for shift in day_shifts)
        due = datetime.combine(day, working_day.shift_start, first_in.tzinfo)
        late = max(first_in - due, NONE) if workday else NONE
        short = max(full_day - worked, NONE) if workday and day != running else NONE
        if late == NONE and short <= working_day.early_leave_grace:
            short = NONE
        days.append(Day(day, worked, worked - ordinary, first_in, last_out, late, short))
    return tuple(days)


def _unmeasured(day: date, day_shifts: list[Shift]) -> Day:
    worked = sum((shift.worked(shift.end) for shift in day_shifts), NONE)
    return Day(day, worked, NONE, min(s.start for s in day_shifts), max(s.end for s in day_shifts), NONE, NONE)
