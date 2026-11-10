from dataclasses import replace
from datetime import datetime, timedelta

from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.punctuality import Punctuality
from chronata.timekeeping.hours.timesheet import days_so_far
from chronata.timekeeping.shifts.durations import NONE
from chronata.timekeeping.shifts.shifts import Break, Shift


def lateness_made_up_by(stretch: Break, shift: Shift, all_shifts: list[Shift], hours: LabelHours, now: datetime) -> timedelta:
    if shift.end is None:
        return NONE
    as_clocked = _punctuality(shift, all_shifts, hours, now)
    if as_clocked is None or as_clocked.short >= as_clocked.late:
        return NONE
    without_the_stretch = _punctuality(shift, _with_break_in(shift, stretch, all_shifts), hours, now)
    return max(without_the_stretch.short - as_clocked.short, NONE)


def _punctuality(shift: Shift, all_shifts: list[Shift], hours: LabelHours, now: datetime) -> Punctuality | None:
    days = days_so_far(all_shifts, hours, now)
    day_of_the_shift = (shift.start.date(), hours.counted_under(shift.label))
    if day_of_the_shift not in days:
        return None
    return days[day_of_the_shift].punctuality


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
