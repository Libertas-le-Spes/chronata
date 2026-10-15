from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

WEEKDAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
MONDAY_TO_FRIDAY = frozenset(range(5))


@dataclass(frozen=True)
class Lunch:
    start: time
    minutes: int


@dataclass(frozen=True)
class WorkingDay:
    shift_start: time
    shift_end: time
    lunch: Lunch | None = None
    workdays: frozenset[int] = MONDAY_TO_FRIDAY
    weekly_limit: float | None = None
    early_leave_grace: timedelta = timedelta(minutes=7)

    @property
    def daily_hours(self) -> float:
        shift = datetime.combine(date.min, self.shift_end) - datetime.combine(date.min, self.shift_start)
        return (shift - timedelta(minutes=self.lunch.minutes if self.lunch else 0)) / timedelta(hours=1)

    @property
    def weekly_hours(self) -> float:
        return self.weekly_limit or self.daily_hours * len(self.workdays)

    def due_by(self, moment: time) -> timedelta:
        until = min(max(moment, self.shift_start), self.shift_end)
        due = _between(self.shift_start, until)
        if self.lunch:
            lunch_end = (datetime.combine(date.min, self.lunch.start) + timedelta(minutes=self.lunch.minutes)).time()
            due -= _between(self.lunch.start, min(max(until, self.lunch.start), lunch_end))
        return due

    def before_end_of_workday(self, moment: datetime) -> bool:
        return moment.weekday() in self.workdays and moment.time() < self.shift_end

    def lunch_on(self, day: date, zone) -> tuple[datetime, datetime] | None:
        if self.lunch is None:
            return None
        begins = datetime.combine(day, self.lunch.start, zone)
        return begins, begins + timedelta(minutes=self.lunch.minutes)


def _between(start: time, end: time) -> timedelta:
    return datetime.combine(date.min, end) - datetime.combine(date.min, start)


def check_fits(shift_start: time, shift_end: time, lunch: Lunch | None) -> None:
    if shift_end <= shift_start:
        raise ValueError("the shift has to end after it starts")
    if lunch is None:
        return
    length = datetime.combine(date.min, shift_end) - datetime.combine(date.min, shift_start)
    if lunch.minutes * 60 >= length.total_seconds():
        raise ValueError("lunch is as long as the whole shift")
    if not shift_start <= lunch.start < shift_end:
        raise ValueError("lunch has to start during the shift")
