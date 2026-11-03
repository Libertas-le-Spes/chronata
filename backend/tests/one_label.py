from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.timesheet import weeks_by_label
from chronata.timekeeping.hours.week import Week
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.shifts.shifts import Shift


def weeks(shifts: list[Shift], working_day: WorkingDay | None) -> list[Week]:
    hours = LabelHours("", {shift.label: working_day for shift in shifts})
    for label_weeks in weeks_by_label(shifts, hours).values():
        return label_weeks
    return []
