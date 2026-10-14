from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from chronata.shifts import Shift

NONE = timedelta()


@dataclass(frozen=True)
class Rules:
    shift_start: time
    shift_end: time
    lunch_start: time
    lunch_minutes: int
    workdays: frozenset[int]
    weekly_hours: float
    configured: bool

    @property
    def daily_hours(self) -> float:
        shift = datetime.combine(date.min, self.shift_end) - datetime.combine(date.min, self.shift_start)
        return (shift - timedelta(minutes=self.lunch_minutes)) / timedelta(hours=1)

    def lunch_overlap(self, start: datetime, end: datetime) -> timedelta:
        lunch_begins = datetime.combine(start.date(), self.lunch_start, start.tzinfo)
        lunch_ends = lunch_begins + timedelta(minutes=self.lunch_minutes)
        return max(min(end, lunch_ends) - max(start, lunch_begins), NONE)

    def worked(self, start: datetime, end: datetime) -> timedelta:
        return end - start - self.lunch_overlap(start, end)


@dataclass(frozen=True)
class Day:
    date: date
    worked: timedelta
    overtime: timedelta


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


def weeks(completed_shifts: list[Shift], rules: Rules) -> list[Week]:
    per_day: dict[date, timedelta] = defaultdict(timedelta)
    for shift in completed_shifts:
        per_day[shift.start.date()] += rules.worked(shift.start, shift.end)
    per_week: dict[date, list[tuple[date, timedelta]]] = defaultdict(list)
    for day, worked in sorted(per_day.items()):
        per_week[day - timedelta(days=day.weekday())].append((day, worked))
    return [Week(start, _days(worked_days, rules)) for start, worked_days in sorted(per_week.items())]


def _days(worked_days: list[tuple[date, timedelta]], rules: Rules) -> tuple[Day, ...]:
    daily_limit = timedelta(hours=rules.daily_hours)
    weekly_room = timedelta(hours=rules.weekly_hours)
    days = []
    for day, worked in worked_days:
        ordinary = min(worked, daily_limit) if day.weekday() in rules.workdays else NONE
        ordinary = min(ordinary, weekly_room)
        weekly_room -= ordinary
        days.append(Day(day, worked, worked - ordinary))
    return tuple(days)
