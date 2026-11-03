from datetime import datetime, time, timedelta

from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.measuring_moment import MeasuringMoment
from chronata.timekeeping.hours.overtime import beyond
from chronata.timekeeping.hours.punctuality import Punctuality, judged, started_after_shift
from chronata.timekeeping.hours.weekly_allowance import WeeklyAllowance
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.shifts.durations import NONE


class Workday:
    def __init__(self, working_day: WorkingDay):
        self.working_day = working_day

    def measure(self, clocked: ClockedDay, allowance: WeeklyAllowance, moment: MeasuringMoment) -> Day:
        worked = clocked.worked
        full_day = timedelta(hours=self.working_day.daily_hours)
        judged_at = moment.judged_at(clocked, self.working_day)
        short_of_due = max(self._due(full_day, judged_at) - worked, NONE)
        punctuality = self._punctuality(clocked, short_of_due)
        overtime = beyond(worked, allowance.normal_part(worked, full_day))
        return Day(clocked.date, worked, overtime, clocked.first_in, clocked.last_out, punctuality, judged_at is not None)

    def _punctuality(self, clocked: ClockedDay, short_of_due: timedelta) -> Punctuality:
        if clocked.started_after(self.working_day.shift_end):
            return started_after_shift(short_of_due)
        return judged(self._late(clocked), short_of_due, self.working_day.early_leave_grace)

    def _late(self, clocked: ClockedDay) -> timedelta:
        if not clocked.lateness_counts(self.working_day.shift_start, self.working_day.shift_end):
            return NONE
        shift_start = datetime.combine(clocked.date, self.working_day.shift_start, clocked.first_in.tzinfo)
        return max(clocked.first_in - shift_start, NONE)

    def _due(self, full_day: timedelta, judged_at: time | None) -> timedelta:
        if judged_at is None:
            return full_day
        return self.working_day.due_by(judged_at)
