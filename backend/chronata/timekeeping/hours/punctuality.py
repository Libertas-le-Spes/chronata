from dataclasses import dataclass
from datetime import timedelta

from chronata.timekeeping.hours.overtime import NONE


@dataclass(frozen=True)
class Punctuality:
    late: timedelta = NONE
    short: timedelta = NONE

    @property
    def made_up(self) -> bool:
        return self.late > NONE and self.short == NONE

    @property
    def worth_noting(self) -> bool:
        return self.late > NONE or self.short > NONE


def judged(late: timedelta, short_of_due: timedelta, early_leave_grace: timedelta) -> Punctuality:
    if late == NONE and short_of_due <= early_leave_grace:
        return Punctuality(late, NONE)
    return Punctuality(late, short_of_due)
