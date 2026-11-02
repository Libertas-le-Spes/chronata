from dataclasses import dataclass
from datetime import date, datetime, timedelta

from chronata.timekeeping.hours.overtime import Overtime
from chronata.timekeeping.hours.punctuality import Punctuality


@dataclass(frozen=True)
class Day:
    date: date
    worked: timedelta
    overtime: Overtime
    first_in: datetime
    last_out: datetime
    punctuality: Punctuality
    running: bool = False

    @property
    def normal(self) -> timedelta:
        return self.worked - self.overtime.earned
