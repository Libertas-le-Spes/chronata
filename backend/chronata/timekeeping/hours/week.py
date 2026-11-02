from dataclasses import dataclass
from datetime import date, timedelta

from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.overtime import NONE, Overtime, total


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
    def overtime(self) -> Overtime:
        return total(day.overtime for day in self.days)


def week_starting(day: date) -> date:
    return day - timedelta(days=day.weekday())
