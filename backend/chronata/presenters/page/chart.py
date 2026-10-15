from datetime import date, datetime, timedelta

from chronata.presenters.page.facts import PageFacts
from chronata.timekeeping.hours.overtime import Week, combined, weeks_by_label
from chronata.timekeeping.shifts.durations import minutes
from chronata.timekeeping.shifts.shifts import Shift

WEEKS_SHOWN = 8


def state(facts: PageFacts) -> dict:
    running = None if facts.interrupted else facts.current
    now = facts.now
    all_weeks = combined(weeks_by_label(facts.shifts, facts.hours, now), facts.hours.default_label)
    recent: dict[date, Week | None] = {week.start: week for week in all_weeks[-WEEKS_SHOWN:]}
    recent.setdefault(now.date() - timedelta(days=now.weekday()), None)
    return {"chart": {
        "targetMinutes": round(facts.hours.main.daily_hours * 60) if facts.hours.main else 0,
        "weeks": [
            {"start": start.isoformat(), "days": [_day(start + timedelta(days=i), week, now, running) for i in range(7)]}
            for start, week in sorted(recent.items())
        ],
    }}


def _day(day: date, week: Week | None, now: datetime, running: Shift | None) -> dict:
    found = next((d for d in week.days if d.date == day), None) if week else None
    when = {"date": day.isoformat(), "soFar": bool(running) and day == now.date(), "future": day > now.date()}
    if found is None:
        return {**when, "normal": 0, "overtime": 0, "late": 0, "short": 0, "madeUp": False}
    return {**when, "normal": minutes(found.worked - found.overtime), "overtime": minutes(found.overtime),
            "late": minutes(found.late), "short": minutes(found.short), "madeUp": found.made_up}
