from dataclasses import dataclass
from datetime import datetime

from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.shifts.shifts import Shift


@dataclass(frozen=True)
class PastTheShiftEnd:
    shift_end: datetime
    wording: str = "past the end of your shift"

    def reached_by(self, back: datetime) -> bool:
        return back > self.shift_end


@dataclass(frozen=True)
class OnADayOff:
    wording: str = "on your day off"

    def reached_by(self, back: datetime) -> bool:
        return True


@dataclass(frozen=True)
class WithoutSetHours:
    wording: str = "on a label without set hours"

    def reached_by(self, back: datetime) -> bool:
        return True


def occasion_of(hours: LabelHours, current: Shift) -> PastTheShiftEnd | OnADayOff | WithoutSetHours:
    working_day = hours.for_label(current.label)
    if working_day is None:
        return WithoutSetHours()
    started = current.start.date()
    if started.weekday() not in working_day.workdays:
        return OnADayOff()
    return PastTheShiftEnd(datetime.combine(started, working_day.shift_end, current.start.tzinfo))
