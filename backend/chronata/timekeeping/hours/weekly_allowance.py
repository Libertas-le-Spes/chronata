from dataclasses import dataclass
from datetime import timedelta

from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.shifts.durations import NONE


@dataclass(frozen=True)
class WeeklyAllowance:
    left: timedelta

    def normal_part(self, worked: timedelta, full_day: timedelta) -> timedelta:
        return min(worked, full_day, self.left)

    def after(self, normal: timedelta) -> "WeeklyAllowance":
        return WeeklyAllowance(self.left - normal)


def allowance_of(working_day: WorkingDay | None) -> WeeklyAllowance:
    if working_day is None:
        return WeeklyAllowance(NONE)
    return WeeklyAllowance(timedelta(hours=working_day.weekly_hours))
