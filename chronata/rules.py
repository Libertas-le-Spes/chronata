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

    def lunch_taken(self, segments: list[tuple[datetime, datetime]]) -> timedelta:
        return sum((self.lunch_overlap(begins, ends) for begins, ends in segments), NONE)

    def worked(self, segments: list[tuple[datetime, datetime]]) -> timedelta:
        return sum((ends - begins for begins, ends in segments), NONE) - self.lunch_taken(segments)


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


def worked_by_label(completed_shifts: list[Shift], rules: Rules) -> dict[str, timedelta]:
    totals: dict[str, timedelta] = defaultdict(timedelta)
    for shift in completed_shifts:
        totals[shift.label] += rules.worked(shift.segments(shift.end))
    return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))


def weeks(completed_shifts: list[Shift], rules: Rules) -> list[Week]:
    per_day: dict[date, list[Shift]] = defaultdict(list)
    for shift in completed_shifts:
        per_day[shift.start.date()].append(shift)
    per_week: dict[date, list[tuple[date, list[Shift]]]] = defaultdict(list)
    for day, day_shifts in sorted(per_day.items()):
        per_week[day - timedelta(days=day.weekday())].append((day, day_shifts))
    return [Week(start, _days(worked_days, rules)) for start, worked_days in sorted(per_week.items())]


def _days(worked_days: list[tuple[date, list[Shift]]], rules: Rules) -> tuple[Day, ...]:
    daily_limit = timedelta(hours=rules.daily_hours)
    weekly_room = timedelta(hours=rules.weekly_hours)
    days = []
    for day, day_shifts in worked_days:
        worked = sum((rules.worked(shift.segments(shift.end)) for shift in day_shifts), NONE)
        workday = day.weekday() in rules.workdays
        ordinary = min(worked, daily_limit) if workday else NONE
        ordinary = min(ordinary, weekly_room)
        weekly_room -= ordinary
        first_in = min(shift.start for shift in day_shifts)
        last_out = max(shift.end for shift in day_shifts)
        due = datetime.combine(day, rules.shift_start, first_in.tzinfo)
        late = max(first_in - due, NONE) if workday else NONE
        short = max(daily_limit - worked, NONE) if workday else NONE
        days.append(Day(day, worked, worked - ordinary, first_in, last_out, late, short))
    return tuple(days)
