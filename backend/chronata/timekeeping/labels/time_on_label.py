from dataclasses import dataclass
from datetime import date, datetime, timedelta

from chronata.timekeeping.hours.week import week_starting
from chronata.timekeeping.shifts.durations import NONE
from chronata.timekeeping.shifts.shifts import Shift


@dataclass
class TimeOnLabel:
    label: str
    this_week: timedelta = NONE
    all_time: timedelta = NONE
    open_now: bool = False

    def add(self, shift: Shift, monday: date, now: datetime) -> None:
        worked = shift.worked(_end_or_now(shift, now))
        self.all_time += worked
        if shift.start.date() >= monday:
            self.this_week += worked
        if shift.end is None:
            self.open_now = True


def hours_by_label(all_shifts: list[Shift], now: datetime) -> list[TimeOnLabel]:
    monday = week_starting(now.date())
    by_label: dict[str, TimeOnLabel] = {}
    for shift in all_shifts:
        if shift.voided:
            continue
        by_label.setdefault(shift.label, TimeOnLabel(shift.label)).add(shift, monday, now)
    return sorted(by_label.values(), key=_most_worked_first)


def _most_worked_first(time_on_label: TimeOnLabel) -> timedelta:
    return -time_on_label.all_time


def _end_or_now(shift: Shift, now: datetime) -> datetime:
    if shift.end is None:
        return now
    return shift.end
