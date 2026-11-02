from dataclasses import dataclass
from datetime import date, timedelta

from chronata.timekeeping.hours.week import Week
from chronata.timekeeping.shifts.durations import NONE


@dataclass(frozen=True)
class LatenessOffset:
    date: date
    late: timedelta


def lateness_offsets(all_weeks: list[Week]) -> list[LatenessOffset]:
    found = []
    for week in all_weeks:
        for day in week.days:
            if day.lateness_taken_off > NONE:
                found.append(LatenessOffset(day.date, day.lateness_taken_off))
    return found
