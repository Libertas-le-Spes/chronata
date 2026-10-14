import re
from datetime import date, datetime, time

LUNCH_QUESTION = "When is lunch, and how long is it?"
SHIFT_QUESTION = "When does your shift start and end?"
DEFAULT_LUNCH = "12:00 for 60 min"
DEFAULT_SHIFT = "08:00 to 17:00"

CLOCK = re.compile(r"(\d{1,2})(?:[:h.](\d{2}))?\s*(am|pm)?", re.IGNORECASE)
LENGTH = re.compile(r"(\d+(?:\.\d+)?)\s*(h|hr|hrs|hour|hours|m|min|mins|minutes)?\s*(?:(\d+)\s*(?:m|min|mins|minutes)?)?\s*$", re.IGNORECASE)


def lunch(answer: str) -> tuple[time, int]:
    text = answer.strip() or DEFAULT_LUNCH
    found = CLOCK.match(text)
    if not found:
        raise ValueError(f"'{text}' needs a time and a length, like 12:00 for 60 min")
    rest = re.sub(r"^\s*(for|,|-)?\s*", "", text[found.end():])
    length = LENGTH.match(rest)
    if not rest or not length:
        raise ValueError(f"'{text}' needs a length after the time, like 12:00 for 60 min or 12h00 1h")
    amount, unit, extra = float(length.group(1)), (length.group(2) or "min").lower(), length.group(3)
    minutes = round(amount * 60) + int(extra or 0) if unit.startswith("h") else round(amount)
    if not 0 <= minutes <= 240:
        raise ValueError("lunch has to be between 0 and 4 hours")
    return _clock(found), minutes


def shift(answer: str) -> tuple[time, time]:
    text = answer.strip() or DEFAULT_SHIFT
    found = list(CLOCK.finditer(text))
    if len(found) != 2:
        raise ValueError(f"'{text}' needs a start and an end, like 08:00 to 17:00")
    start, end = _clock(found[0]), _clock(found[1])
    if end <= start:
        raise ValueError("the shift has to end after it starts")
    return start, end


def check_fit(shift_start: time, shift_end: time, lunch_start: time, lunch_minutes: int) -> None:
    length = datetime.combine(date.min, shift_end) - datetime.combine(date.min, shift_start)
    if lunch_minutes * 60 >= length.total_seconds():
        raise ValueError("lunch is as long as the whole shift")
    if not shift_start <= lunch_start < shift_end:
        raise ValueError("lunch has to start during the shift")


def _clock(found: re.Match) -> time:
    hour, minute, meridiem = int(found.group(1)), int(found.group(2) or 0), (found.group(3) or "").lower()
    if meridiem == "pm" and hour < 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        raise ValueError(f"'{found.group(0)}' is not a time of day")
    return time(hour, minute)
