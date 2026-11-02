from datetime import date, datetime, timedelta

from chronata.presenters.page.facts import PageFacts
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.timesheet import combined, weeks_by_label
from chronata.timekeeping.hours.week import Week, week_starting
from chronata.timekeeping.shifts.durations import minutes
from chronata.timekeeping.shifts.shifts import Shift

WEEKS_SHOWN = 8


def state(facts: PageFacts) -> dict:
    now = facts.now
    running = _running(facts)
    shown = []
    for start, week in _recent_weeks(facts):
        days = [_day(start + timedelta(days=offset), week, now, running) for offset in range(7)]
        shown.append({"start": start.isoformat(), "days": days})
    return {"chart": {"targetMinutes": _target_minutes(facts.hours), "weeks": shown}}


def _running(facts: PageFacts) -> Shift | None:
    if facts.interrupted:
        return None
    return facts.current


def _recent_weeks(facts: PageFacts) -> list[tuple[date, Week | None]]:
    all_weeks = combined(weeks_by_label(facts.shifts, facts.hours, facts.now), facts.hours.default_label)
    recent: dict[date, Week | None] = {}
    first_shown = max(len(all_weeks) - WEEKS_SHOWN, 0)
    for week in all_weeks[first_shown:]:
        recent[week.start] = week
    recent.setdefault(week_starting(facts.now.date()), None)
    return sorted(recent.items())


def _target_minutes(hours: LabelHours) -> int:
    if hours.main is None:
        return 0
    return round(hours.main.daily_hours * 60)


def _day(day: date, week: Week | None, now: datetime, running: Shift | None) -> dict:
    when = {"date": day.isoformat(), "soFar": running is not None and day == now.date(), "future": day > now.date()}
    found = _found(day, week)
    if found is None:
        return {**when, "normal": 0, "overtime": 0, "late": 0, "short": 0, "madeUp": False}
    punctuality = found.punctuality
    return {**when, "normal": minutes(found.normal), "overtime": minutes(found.overtime.earned),
            "late": minutes(punctuality.late), "short": minutes(punctuality.short), "madeUp": punctuality.made_up}


def _found(day: date, week: Week | None) -> Day | None:
    if week is None:
        return None
    for measured in week.days:
        if measured.date == day:
            return measured
    return None
