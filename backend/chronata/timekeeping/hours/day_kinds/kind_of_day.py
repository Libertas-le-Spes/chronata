from datetime import date

from chronata.timekeeping.hours.day_kinds.day_off import DayOff
from chronata.timekeeping.hours.day_kinds.workday import Workday
from chronata.timekeeping.hours.working_day import WorkingDay


def kind_of_day(working_day: WorkingDay, day: date) -> Workday | DayOff:
    if day.weekday() in working_day.workdays:
        return Workday(working_day)
    return DayOff()
