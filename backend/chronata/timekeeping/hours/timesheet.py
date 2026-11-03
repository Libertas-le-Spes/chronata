from collections import defaultdict
from dataclasses import replace
from datetime import date, datetime

from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.day_kinds.kind_of_day import kind_of_day
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.measuring_moment import MeasuringMoment
from chronata.timekeeping.hours.week import Week, week_starting
from chronata.timekeeping.hours.weekly_allowance import WeeklyAllowance, allowance_of
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.shifts.shifts import Shift, completed, open_shift


def _label_weeks(finished_shifts: list[Shift], working_day: WorkingDay | None, moment: MeasuringMoment,
                 day_starts: dict[date, datetime]) -> list[Week]:
    found = []
    for start, clocked_days in _clocked_days_by_week(finished_shifts, day_starts):
        days, allowance = _measured(clocked_days, working_day, moment)
        found.append(Week(start, days, allowance.left))
    return found


def weeks_by_label(all_shifts: list[Shift], hours: LabelHours, now: datetime | None = None) -> dict[str, list[Week]]:
    counted = completed(all_shifts)
    clocked_in_on = None
    today = _running_today(all_shifts, now)
    if today is not None:
        counted.append(replace(today, end=now))
        clocked_in_on = hours.counted_under(today.label)
    grouped: dict[str, list[Shift]] = defaultdict(list)
    for shift in counted:
        grouped[hours.counted_under(shift.label)].append(shift)
    day_starts = _day_starts(counted)
    by_label = {}
    for label, label_shifts in grouped.items():
        by_label[label] = _label_weeks(label_shifts, hours.for_label(label), MeasuringMoment(now, label == clocked_in_on), day_starts)
    return by_label


def days_so_far(all_shifts: list[Shift], hours: LabelHours, now: datetime) -> dict[tuple[date, str], Day]:
    found = {}
    for label, label_weeks in weeks_by_label(all_shifts, hours, now).items():
        for week in label_weeks:
            for day in week.days:
                found[(day.date, label)] = day
    return found


def _clocked_days_by_week(shifts: list[Shift], day_starts: dict[date, datetime]) -> list[tuple[date, list[ClockedDay]]]:
    per_day: dict[date, list[Shift]] = defaultdict(list)
    for shift in shifts:
        per_day[shift.start.date()].append(shift)
    per_week: dict[date, list[ClockedDay]] = defaultdict(list)
    for day in sorted(per_day):
        clocked = tuple(per_day[day])
        opened_the_day = min(shift.start for shift in clocked) <= day_starts[day]
        per_week[week_starting(day)].append(ClockedDay(day, clocked, opened_the_day))
    return sorted(per_week.items())


def _earlier_than_known(starts: dict[date, datetime], day: date, start: datetime) -> bool:
    if day not in starts:
        return True
    return start < starts[day]


def _day_starts(shifts: list[Shift]) -> dict[date, datetime]:
    starts: dict[date, datetime] = {}
    for shift in shifts:
        day = shift.start.date()
        if _earlier_than_known(starts, day, shift.start):
            starts[day] = shift.start
    return starts


def _measured(clocked_days: list[ClockedDay], working_day: WorkingDay | None, moment: MeasuringMoment) -> tuple[tuple[Day, ...], WeeklyAllowance]:
    allowance = allowance_of(working_day)
    days = []
    for clocked in clocked_days:
        day = kind_of_day(working_day, clocked).measure(clocked, allowance, moment)
        allowance = allowance.after(day.normal)
        days.append(day)
    return tuple(days), allowance


def _running_today(all_shifts: list[Shift], now: datetime | None) -> Shift | None:
    running = open_shift(all_shifts)
    if running is None or now is None:
        return None
    if running.start.date() != now.date():
        return None
    return running
