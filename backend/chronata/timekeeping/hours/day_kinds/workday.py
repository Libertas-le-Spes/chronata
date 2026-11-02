from datetime import datetime, time, timedelta

from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.overtime import NONE, beyond
from chronata.timekeeping.hours.punctuality import judged
from chronata.timekeeping.hours.weekly_allowance import WeeklyAllowance
from chronata.timekeeping.hours.working_day import WorkingDay


class Workday:
    def __init__(self, working_day: WorkingDay):
        self.working_day = working_day

    def measure(self, clocked: ClockedDay, allowance: WeeklyAllowance, judged_at: time | None) -> Day:
        worked = clocked.worked
        full_day = timedelta(hours=self.working_day.daily_hours)
        short_of_due = max(self._due(full_day, judged_at) - worked, NONE)
        punctuality = judged(self._late(clocked), short_of_due, self.working_day.early_leave_grace)
        overtime = beyond(worked, allowance.normal_part(worked, full_day))
        return Day(clocked.date, worked, overtime, clocked.first_in, clocked.last_out, punctuality, judged_at is not None)

    def _late(self, clocked: ClockedDay) -> timedelta:
        shift_start = datetime.combine(clocked.date, self.working_day.shift_start, clocked.first_in.tzinfo)
        return max(clocked.first_in - shift_start, NONE)

    def _due(self, full_day: timedelta, judged_at: time | None) -> timedelta:
        if judged_at is None:
            return full_day
        return self.working_day.due_by(judged_at)
