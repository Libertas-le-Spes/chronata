from datetime import time

from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.overtime import Overtime
from chronata.timekeeping.hours.punctuality import Punctuality
from chronata.timekeeping.hours.weekly_allowance import WeeklyAllowance


class DayOff:
    def measure(self, clocked: ClockedDay, allowance: WeeklyAllowance, judged_at: time | None) -> Day:
        worked = clocked.worked
        return Day(clocked.date, worked, Overtime(worked), clocked.first_in, clocked.last_out, Punctuality(), judged_at is not None)
