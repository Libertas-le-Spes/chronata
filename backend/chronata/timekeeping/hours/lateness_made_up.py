from dataclasses import replace
from datetime import datetime, timedelta

from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.timesheet import days_so_far
from chronata.timekeeping.shifts.durations import NONE
from chronata.timekeeping.shifts.shifts import Break, Shift


def lateness_made_up_by(stretch: Break, shift: Shift, all_shifts: list[Shift], hours: LabelHours, now: datetime) -> timedelta:
    as_clocked = _uncovered_lateness(shift, all_shifts, hours, now)
    without_the_stretch = _uncovered_lateness(shift, _with_break_in(shift, stretch, all_shifts), hours, now)
    return without_the_stretch - as_clocked


def _uncovered_lateness(shift: Shift, all_shifts: list[Shift], hours: LabelHours, now: datetime) -> timedelta:
    days = days_so_far(all_shifts, hours, now)
    day_of_the_shift = (shift.start.date(), hours.counted_under(shift.label))
    if day_of_the_shift not in days:
        return NONE
    return days[day_of_the_shift].punctuality.uncovered_lateness


def _with_break_in(target: Shift, stretch: Break, all_shifts: list[Shift]) -> list[Shift]:
    changed = []
    for shift in all_shifts:
        if shift.id == target.id:
            changed.append(_copy_with_break(shift, stretch))
        else:
            changed.append(shift)
    return changed


def _copy_with_break(shift: Shift, stretch: Break) -> Shift:
    copy = replace(shift, breaks=list(shift.breaks))
    copy.add_break(stretch)
    return copy
