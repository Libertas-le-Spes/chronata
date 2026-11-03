from dataclasses import dataclass
from datetime import date, timedelta

from chronata.timekeeping.hours.week import Week
from chronata.timekeeping.shifts.durations import NONE


@dataclass(frozen=True)
class UncoveredLateness:
    date: date
    amount: timedelta


def uncovered_lateness(all_weeks: list[Week]) -> list[UncoveredLateness]:
    found = []
    for week in all_weeks:
        found += _in_week(week)
    return found


def _in_week(week: Week) -> list[UncoveredLateness]:
    not_yet_absorbed = week.unused_allowance
    found = []
    for day in week.days:
        amount = min(day.uncovered_lateness, not_yet_absorbed)
        if amount > NONE:
            found.append(UncoveredLateness(day.date, amount))
            not_yet_absorbed -= amount
    return found
