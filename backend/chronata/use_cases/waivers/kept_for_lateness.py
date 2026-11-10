from datetime import datetime, timedelta

from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.shifts.durations import NONE
from chronata.timekeeping.shifts.shifts import Shift
from chronata.use_cases.waivers.stretch import Stretch


def kept_for_lateness(asked: Stretch, made_up: timedelta, hours: LabelHours) -> Stretch | None:
    if made_up <= NONE:
        return None
    shift_end = _shift_end_on_the_day_of(asked.shift, hours)
    if shift_end is None:
        return None
    after_the_shift = asked.from_moment(shift_end)
    if after_the_shift.length <= NONE:
        return None
    return after_the_shift.first(made_up)


def waived_pieces(asked: Stretch, kept: Stretch | None) -> list[Stretch]:
    if kept is None:
        return [asked]
    return asked.without(kept)


def _shift_end_on_the_day_of(shift: Shift, hours: LabelHours) -> datetime | None:
    working_day = hours.for_label(shift.label)
    if working_day is None:
        return None
    return datetime.combine(shift.start.date(), working_day.shift_end, shift.start.tzinfo)
