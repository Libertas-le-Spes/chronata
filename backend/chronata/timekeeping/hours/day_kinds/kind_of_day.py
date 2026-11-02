from datetime import date
from typing import Protocol

from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.day_kinds.day_off import DayOff
from chronata.timekeeping.hours.day_kinds.hours_not_set import HoursNotSet
from chronata.timekeeping.hours.day_kinds.workday import Workday
from chronata.timekeeping.hours.measuring_moment import MeasuringMoment
from chronata.timekeeping.hours.weekly_allowance import WeeklyAllowance
from chronata.timekeeping.hours.working_day import WorkingDay


class KindOfDay(Protocol):
    def measure(self, clocked: ClockedDay, allowance: WeeklyAllowance, moment: MeasuringMoment) -> Day: ...


def kind_of_day(working_day: WorkingDay | None, day: date) -> KindOfDay:
    if working_day is None:
        return HoursNotSet()
    if day.weekday() in working_day.workdays:
        return Workday(working_day)
    return DayOff(working_day)
