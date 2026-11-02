from dataclasses import dataclass
from datetime import timedelta

from chronata.timekeeping.compensation.period import Period
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.overtime import Overtime, total
from chronata.timekeeping.shifts.durations import NONE


@dataclass(frozen=True)
class Reconciliation:
    periods: list[Period]
    unmatched: list[Day]

    @property
    def owed(self) -> Overtime:
        return total(period.owed for period in self.periods) + self.unmatched_overtime

    @property
    def compensated(self) -> timedelta:
        return sum((period.paid + period.time_off for period in self.periods), NONE)

    @property
    def shortfall(self) -> timedelta:
        return sum((period.shortfall for period in self.periods), NONE)

    @property
    def unmatched_overtime(self) -> Overtime:
        return total(day.overtime for day in self.unmatched)
