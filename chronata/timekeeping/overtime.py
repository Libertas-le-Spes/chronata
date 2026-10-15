from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta

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
    running: bool = False

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


def weeks(finished_shifts: list[Shift], working_day: WorkingDay | None, now: datetime | None = None, clocked_in: bool = False) -> list[Week]:
    per_day: dict[date, list[Shift]] = defaultdict(list)
    for shift in finished_shifts:
        per_day[shift.start.date()].append(shift)
    per_week: dict[date, list[tuple[date, list[Shift]]]] = defaultdict(list)
    for day, day_shifts in sorted(per_day.items()):
        per_week[day - timedelta(days=day.weekday())].append((day, day_shifts))
    return [Week(start, _days(worked_days, working_day, now, clocked_in)) for start, worked_days in sorted(per_week.items())]


def weeks_by_label(all_shifts: list[Shift], hours: LabelHours, now: datetime | None = None) -> dict[str, list[Week]]:
    running = open_shift(all_shifts)
    today = running if running and now and running.start.date() == now.date() else None
    counted = completed(all_shifts) + ([replace(today, end=now)] if today else [])
    grouped: dict[str, list[Shift]] = defaultdict(list)
    for shift in counted:
        grouped[shift.label or hours.default_label].append(shift)
    clocked_in_on = (today.label or hours.default_label) if today else None
    return {label: weeks(label_shifts, hours.for_label(label), now, label == clocked_in_on) for label, label_shifts in grouped.items()}


def days_so_far(all_shifts: list[Shift], hours: LabelHours, now: datetime) -> dict[tuple[date, str], Day]:
    by_label = weeks_by_label(all_shifts, hours, now)
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
            any(d.running for _, d in found),
        ))
    return [Week(start, tuple(days)) for start, days in sorted(merged.items())]


def _days(worked_days: list[tuple[date, list[Shift]]], working_day: WorkingDay | None, now: datetime | None, clocked_in: bool) -> tuple[Day, ...]:
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
        late = max(first_in - datetime.combine(day, working_day.shift_start, first_in.tzinfo), NONE) if workday else NONE
        judged_at = _judged_at(day, working_day, last_out, now, clocked_in)
        due = full_day if judged_at is None else working_day.due_by(judged_at)
        short = max(due - worked, NONE) if workday else NONE
        if late == NONE and short <= working_day.early_leave_grace:
            short = NONE
        days.append(Day(day, worked, worked - ordinary, first_in, last_out, late, short, judged_at is not None))
    return tuple(days)


def _judged_at(day: date, working_day: WorkingDay, last_out: datetime, now: datetime | None, clocked_in: bool) -> time | None:
    if now is None or day != now.date() or (not clocked_in and now.time() >= working_day.shift_end):
        return None
    return now.time() if clocked_in else last_out.time()


def _unmeasured(day: date, day_shifts: list[Shift]) -> Day:
    worked = sum((shift.worked(shift.end) for shift in day_shifts), NONE)
    return Day(day, worked, NONE, min(s.start for s in day_shifts), max(s.end for s in day_shifts), NONE, NONE)
