from dataclasses import dataclass
from datetime import timedelta

from chronata.timekeeping.shifts.durations import NONE


@dataclass(frozen=True)
class Punctuality:
    late: timedelta = NONE
    short: timedelta = NONE

    @property
    def arrived_late(self) -> bool:
        return self.late > NONE

    @property
    def made_up(self) -> bool:
        return self.arrived_late and self.short == NONE

    @property
    def uncovered_lateness(self) -> timedelta:
        if not self.arrived_late:
            return NONE
        return min(self.late, self.short)

    @property
    def worth_noting(self) -> bool:
        return self.late > NONE or self.short > NONE


def judged(late: timedelta, short_of_due: timedelta, early_leave_grace: timedelta) -> Punctuality:
    if late == NONE and short_of_due <= early_leave_grace:
        return Punctuality(late, NONE)
    return Punctuality(late, short_of_due)
