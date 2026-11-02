from collections import defaultdict
from dataclasses import replace
from datetime import date, datetime

from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.day_kinds.hours_not_set import HoursNotSet
from chronata.timekeeping.hours.day_kinds.kind_of_day import kind_of_day
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.measuring_moment import MeasuringMoment
from chronata.timekeeping.hours.overtime import NONE, total
from chronata.timekeeping.hours.punctuality import Punctuality
from chronata.timekeeping.hours.week import Week, week_starting
from chronata.timekeeping.hours.weekly_allowance import allowance_of
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.shifts.shifts import Shift, completed, open_shift


def weeks(finished_shifts: list[Shift], working_day: WorkingDay | None, now: datetime | None = None, clocked_in: bool = False) -> list[Week]:
    moment = MeasuringMoment(now, clocked_in)
    found = []
    for start, clocked_days in _clocked_days_by_week(finished_shifts):
        found.append(Week(start, _measured(clocked_days, working_day, moment)))
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
    by_label = {}
    for label, label_shifts in grouped.items():
        by_label[label] = weeks(label_shifts, hours.for_label(label), now, label == clocked_in_on)
    return by_label


def days_so_far(all_shifts: list[Shift], hours: LabelHours, now: datetime) -> dict[tuple[date, str], Day]:
    found = {}
    for label, label_weeks in weeks_by_label(all_shifts, hours, now).items():
        for week in label_weeks:
            for day in week.days:
                found[(day.date, label)] = day
    return found


def combined(by_label: dict[str, list[Week]], main_label: str) -> list[Week]:
    per_day: dict[date, list[tuple[str, Day]]] = defaultdict(list)
    for label, label_weeks in by_label.items():
        for week in label_weeks:
            for day in week.days:
                per_day[day.date].append((label, day))
    per_week: dict[date, list[Day]] = defaultdict(list)
    for day in sorted(per_day):
        per_week[week_starting(day)].append(_merged(day, per_day[day], main_label))
    return [Week(start, tuple(per_week[start])) for start in sorted(per_week)]


def _clocked_days_by_week(shifts: list[Shift]) -> list[tuple[date, list[ClockedDay]]]:
    per_day: dict[date, list[Shift]] = defaultdict(list)
    for shift in shifts:
        per_day[shift.start.date()].append(shift)
    per_week: dict[date, list[ClockedDay]] = defaultdict(list)
    for day in sorted(per_day):
        per_week[week_starting(day)].append(ClockedDay(day, tuple(per_day[day])))
    return sorted(per_week.items())


def _measured(clocked_days: list[ClockedDay], working_day: WorkingDay | None, moment: MeasuringMoment) -> tuple[Day, ...]:
    if working_day is None:
        return tuple(HoursNotSet().measure(clocked) for clocked in clocked_days)
    allowance = allowance_of(working_day)
    days = []
    for clocked in clocked_days:
        day = kind_of_day(working_day, clocked.date).measure(clocked, allowance, moment.judged_at(clocked, working_day))
        allowance = allowance.after(day.normal)
        days.append(day)
    return tuple(days)


def _merged(day: date, found: list[tuple[str, Day]], main_label: str) -> Day:
    days = [labelled_day for _, labelled_day in found]
    return Day(
        day,
        sum((each.worked for each in days), NONE),
        total(each.overtime for each in days),
        min(each.first_in for each in days),
        max(each.last_out for each in days),
        _punctuality_of(found, main_label),
        any(each.running for each in days),
    )


def _punctuality_of(found: list[tuple[str, Day]], main_label: str) -> Punctuality:
    for label, day in found:
        if label == main_label:
            return day.punctuality
    return Punctuality()


def _running_today(all_shifts: list[Shift], now: datetime | None) -> Shift | None:
    running = open_shift(all_shifts)
    if running is None or now is None:
        return None
    if running.start.date() != now.date():
        return None
    return running
