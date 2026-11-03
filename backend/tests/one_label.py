from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.timesheet import weeks_by_label
from chronata.timekeeping.hours.week import Week
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.shifts.shifts import Shift


def weeks(shifts: list[Shift], working_day: WorkingDay | None) -> list[Week]:
    labels = {shift.label for shift in shifts}
    if len(labels) != 1:
        raise ValueError("these weeks are for shifts on exactly one label")
    label = labels.pop()
    return weeks_by_label(shifts, LabelHours("", {label: working_day}))[label]
