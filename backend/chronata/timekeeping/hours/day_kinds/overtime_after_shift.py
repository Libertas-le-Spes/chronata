from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.measuring_moment import MeasuringMoment
from chronata.timekeeping.hours.overtime import Overtime
from chronata.timekeeping.hours.punctuality import started_after_shift
from chronata.timekeeping.hours.weekly_allowance import WeeklyAllowance
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.shifts.durations import NONE


class OvertimeAfterShift:
    def __init__(self, working_day: WorkingDay):
        self.working_day = working_day

    def measure(self, clocked: ClockedDay, allowance: WeeklyAllowance, moment: MeasuringMoment) -> Day:
        worked = clocked.worked
        running = moment.running(clocked, self.working_day)
        return Day(clocked.date, worked, Overtime(worked), clocked.first_in, clocked.last_out, started_after_shift(NONE), running)
