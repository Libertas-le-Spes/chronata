from dataclasses import dataclass
from datetime import date, datetime, timedelta

from chronata.timekeeping.shifts.durations import NONE
from chronata.timekeeping.shifts.shifts import Shift


@dataclass(frozen=True)
class ClockedDay:
    date: date
    shifts: tuple[Shift, ...]

    @property
    def worked(self) -> timedelta:
        return sum((shift.worked(shift.end) for shift in self.shifts), NONE)

    @property
    def first_in(self) -> datetime:
        return min(shift.start for shift in self.shifts)

    @property
    def last_out(self) -> datetime:
        return max(shift.end for shift in self.shifts)
