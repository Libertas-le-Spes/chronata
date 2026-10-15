from datetime import date, datetime, timedelta

from chronata.entrypoints.web.page_state.snapshot import Snapshot
from chronata.timekeeping.durations import minutes
from chronata.timekeeping.shifts import Shift
from chronata.timekeeping.overtime import Week, combined, weeks_by_label

WEEKS_SHOWN = 8


def state(app, taken: Snapshot) -> dict:
    running = None if taken.interrupted else taken.current
    now = taken.now
    all_weeks = combined(weeks_by_label(taken.shifts, taken.hours, now), taken.hours.default_label)
    recent: dict[date, Week | None] = {week.start: week for week in all_weeks[-WEEKS_SHOWN:]}
    recent.setdefault(now.date() - timedelta(days=now.weekday()), None)
    return {"chart": {
        "targetMinutes": round(taken.hours.main.daily_hours * 60) if taken.hours.main else 0,
        "weeks": [
            {"start": start.isoformat(), "days": [_day(start + timedelta(days=i), week, now, running) for i in range(7)]}
            for start, week in sorted(recent.items())
        ],
    }}


def _day(day: date, week: Week | None, now: datetime, running: Shift | None) -> dict:
    found = next((d for d in week.days if d.date == day), None) if week else None
    return {
        "date": day.isoformat(),
        "normal": minutes(found.worked - found.overtime) if found else 0,
        "overtime": minutes(found.overtime) if found else 0,
        "late": minutes(found.late) if found else 0,
        "short": minutes(found.short) if found else 0,
        "madeUp": bool(found and found.made_up),
        "soFar": bool(running) and day == now.date(),
        "future": day > now.date(),
    }
