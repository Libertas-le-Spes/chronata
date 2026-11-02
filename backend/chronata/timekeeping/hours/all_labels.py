from collections import defaultdict
from datetime import date

from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.overtime import total
from chronata.timekeeping.hours.punctuality import Punctuality
from chronata.timekeeping.hours.week import Week, week_starting
from chronata.timekeeping.shifts.durations import NONE


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
