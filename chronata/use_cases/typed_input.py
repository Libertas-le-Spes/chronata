import re
from datetime import date, datetime, time, timedelta

from chronata.timekeeping.working_day import Lunch, WorkingDay, check_fits
from chronata.use_cases.outcome import UserError

LUNCH_QUESTION = "When is lunch, and how long is it? (leave empty for no lunch)"
SHIFT_QUESTION = "When does your shift start and end?"
DEFAULT_LABEL_QUESTION = "Which client or project is your main one, if any?"
DEFAULT_SHIFT = "08:00 to 17:00"

CLOCK = re.compile(r"(\d{1,2})(?:[:h.](\d{2}))?\s*(am|pm)?", re.IGNORECASE)
LENGTH = re.compile(r"(\d+(?:\.\d+)?)\s*(h|hr|hrs|hour|hours|m|min|mins|minutes)?\s*(?:(\d+)\s*(?:m|min|mins|minutes)?)?\s*$", re.IGNORECASE)


NO_LUNCH = {"", "none", "no", "no lunch", "-"}


def hours(shift_answer: str, lunch_answer: str) -> WorkingDay:
    shift_start, shift_end = shift(shift_answer)
    taken = lunch(lunch_answer)
    try:
        check_fits(shift_start, shift_end, taken)
    except ValueError as error:
        raise UserError(str(error))
    return WorkingDay(shift_start, shift_end, taken)


def lunch(answer: str) -> Lunch | None:
    text = answer.strip()
    if text.lower() in NO_LUNCH:
        return None
    found = CLOCK.match(text)
    if not found:
        raise UserError(f"'{text}' needs a time and a length, like 12:00 for 60 min")
    rest = re.sub(r"^\s*(for|,|-)?\s*", "", text[found.end():])
    length = LENGTH.match(rest)
    if not rest or not length:
        raise UserError(f"'{text}' needs a length after the time, like 12:00 for 60 min or 12h00 1h")
    amount, unit, extra = float(length.group(1)), (length.group(2) or "min").lower(), length.group(3)
    minutes = round(amount * 60) + int(extra or 0) if unit.startswith("h") else round(amount)
    if not 0 <= minutes <= 240:
        raise UserError("lunch has to be between 0 and 4 hours")
    return Lunch(_clock(found), minutes) if minutes else None


def shift(answer: str) -> tuple[time, time]:
    text = answer.strip() or DEFAULT_SHIFT
    found = list(CLOCK.finditer(text))
    if len(found) != 2:
        raise UserError(f"'{text}' needs a start and an end, like 08:00 to 17:00")
    return _clock(found[0]), _clock(found[1])


def day(text: str | None) -> date:
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        raise UserError(f"'{text}' is not a date like 2026-10-14")


def moment(text: str | None, on_day: date, now: datetime, allow_future: bool = False) -> datetime:
    try:
        parsed = datetime.fromisoformat(text) if " " in text or "T" in text else datetime.combine(on_day, time.fromisoformat(text))
    except (TypeError, ValueError):
        raise UserError(f"'{text}' is not a time like 08:04, 08:04:31 or 2026-10-14 08:04")
    parsed = parsed.astimezone()
    if parsed > now and not allow_future:
        raise UserError(f"{parsed:%Y-%m-%d %H:%M:%S} is in the future")
    return parsed


def end_after(start: datetime, text: str, now: datetime) -> datetime:
    end = moment(text, start.date(), now, allow_future=True)
    time_only = " " not in text and "T" not in text
    return end + timedelta(days=1) if time_only and end <= start else end


def required(reason: str | None) -> str:
    if not reason or not reason.strip():
        raise UserError("a reason is required, so the record explains itself")
    return reason.strip()


def _clock(found: re.Match) -> time:
    hour, minute, meridiem = int(found.group(1)), int(found.group(2) or 0), (found.group(3) or "").lower()
    if meridiem == "pm" and hour < 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        raise UserError(f"'{found.group(0)}' is not a time of day")
    return time(hour, minute)
