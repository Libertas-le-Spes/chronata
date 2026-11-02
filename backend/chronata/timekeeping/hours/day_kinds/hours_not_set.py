from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.overtime import Overtime
from chronata.timekeeping.hours.punctuality import Punctuality


class HoursNotSet:
    def measure(self, clocked: ClockedDay) -> Day:
        return Day(clocked.date, clocked.worked, Overtime(), clocked.first_in, clocked.last_out, Punctuality())
