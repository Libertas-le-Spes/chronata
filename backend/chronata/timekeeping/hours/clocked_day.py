from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from chronata.timekeeping.shifts.durations import NONE
from chronata.timekeeping.shifts.shifts import Shift


@dataclass(frozen=True)
class ClockedDay:
    date: date
    shifts: tuple[Shift, ...]
    opened_the_day: bool

    @property
    def worked(self) -> timedelta:
        return sum((shift.worked(shift.end) for shift in self.shifts), NONE)

    @property
    def first_in(self) -> datetime:
        return min(shift.start for shift in self.shifts)

    @property
    def last_out(self) -> datetime:
        return max(shift.end for shift in self.shifts)

    @property
    def first_shift(self) -> Shift:
        return min(self.shifts, key=_start_of)

    @property
    def lateness_counts(self) -> bool:
        if self.opened_the_day:
            return True
        return self.first_shift.start_answer.said_late

    @property
    def worked_as_overtime(self) -> bool:
        return self.first_shift.start_answer.said_overtime

    def started_after(self, shift_end: time) -> bool:
        if not self.opened_the_day:
            return False
        return self.first_in.time() >= shift_end


def _start_of(shift: Shift) -> datetime:
    return shift.start
