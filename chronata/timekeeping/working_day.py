from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from chronata.timekeeping.shifts import Shift

NONE = timedelta()
WEEKDAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclass(frozen=True)
class WorkingDay:
    shift_start: time
    shift_end: time
    lunch_start: time
    lunch_minutes: int
    workdays: frozenset[int]
    weekly_hours: float
    configured: bool
    early_leave_grace: timedelta = timedelta(minutes=7)
    default_label: str = ""

    @property
    def daily_hours(self) -> float:
        shift = datetime.combine(date.min, self.shift_end) - datetime.combine(date.min, self.shift_start)
        return (shift - timedelta(minutes=self.lunch_minutes)) / timedelta(hours=1)

    def before_end_of_workday(self, moment: datetime) -> bool:
        return moment.weekday() in self.workdays and moment.time() < self.shift_end

    def strays_from_default(self, label: str, moment: datetime) -> bool:
        return bool(self.default_label) and moment.weekday() in self.workdays and label != self.default_label

    def lunch_on(self, day: date, zone) -> tuple[datetime, datetime]:
        begins = datetime.combine(day, self.lunch_start, zone)
        return begins, begins + timedelta(minutes=self.lunch_minutes)


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


def check_fits(shift_start: time, shift_end: time, lunch_start: time, lunch_minutes: int) -> None:
    if shift_end <= shift_start:
        raise ValueError("the shift has to end after it starts")
    length = datetime.combine(date.min, shift_end) - datetime.combine(date.min, shift_start)
    if lunch_minutes * 60 >= length.total_seconds():
        raise ValueError("lunch is as long as the whole shift")
    if not shift_start <= lunch_start < shift_end:
        raise ValueError("lunch has to start during the shift")


def worked_by_label(finished_shifts: list[Shift]) -> dict[str, timedelta]:
    totals: dict[str, timedelta] = defaultdict(timedelta)
    for shift in finished_shifts:
        totals[shift.label] += shift.worked(shift.end)
    return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))


def weeks(finished_shifts: list[Shift], working_day: WorkingDay) -> list[Week]:
    per_day: dict[date, list[Shift]] = defaultdict(list)
    for shift in finished_shifts:
        per_day[shift.start.date()].append(shift)
    per_week: dict[date, list[tuple[date, list[Shift]]]] = defaultdict(list)
    for day, day_shifts in sorted(per_day.items()):
        per_week[day - timedelta(days=day.weekday())].append((day, day_shifts))
    return [Week(start, _days(worked_days, working_day)) for start, worked_days in sorted(per_week.items())]


def _days(worked_days: list[tuple[date, list[Shift]]], working_day: WorkingDay) -> tuple[Day, ...]:
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
        short = max(full_day - worked, NONE) if workday else NONE
        if late == NONE and short <= working_day.early_leave_grace:
            short = NONE
        days.append(Day(day, worked, worked - ordinary, first_in, last_out, late, short))
    return tuple(days)
