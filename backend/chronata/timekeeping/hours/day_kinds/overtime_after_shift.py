from datetime import timedelta

from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.day_kinds.workday import Workday
from chronata.timekeeping.hours.punctuality import Punctuality, started_after_shift
from chronata.timekeeping.shifts.durations import NONE


class OvertimeAfterShift(Workday):
    def _punctuality(self, clocked: ClockedDay, short_of_due: timedelta) -> Punctuality:
        return started_after_shift(NONE)
