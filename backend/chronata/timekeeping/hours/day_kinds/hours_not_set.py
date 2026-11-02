from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.measuring_moment import MeasuringMoment
from chronata.timekeeping.hours.overtime import Overtime
from chronata.timekeeping.hours.punctuality import Punctuality
from chronata.timekeeping.hours.weekly_allowance import WeeklyAllowance


class HoursNotSet:
    def measure(self, clocked: ClockedDay, allowance: WeeklyAllowance, moment: MeasuringMoment) -> Day:
        return Day(clocked.date, clocked.worked, Overtime(), clocked.first_in, clocked.last_out, Punctuality())
