import re
from datetime import date, datetime, time, timedelta

from chronata.timekeeping.hours.working_day import Lunch, WorkingDay, check_fits
from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions.questions import Answers

DEFAULT_LABEL_QUESTION = "Which client or project is your main one, if any?"
DIGITS = re.compile(r"\d{1,4}")
LONGEST_LUNCH = 240


def hours(answers: Answers) -> WorkingDay:
    begins, ends = clock(answers.shift_start), clock(answers.shift_end)
    taken = _lunch(answers.lunch_start, answers.lunch_minutes)
    try:
        check_fits(begins, ends, taken)
    except ValueError as error:
        raise UserError(str(error))
    return WorkingDay(begins, ends, taken)


def _lunch(start: str, minutes: str) -> Lunch | None:
    if not start.strip() or not minutes.strip():
        return None
    return Lunch(clock(start), minutes_number(minutes))


def clock(text: str) -> time:
    typed = text.strip()
    if DIGITS.fullmatch(typed):
        return clock_number(typed)
    try:
        return time.fromisoformat(typed).replace(second=0, microsecond=0)
    except ValueError:
        raise UserError(f"'{typed}' is not a time; type it like 830 or 1730")


def clock_number(text: str) -> time:
    digits = text.strip()
    if not DIGITS.fullmatch(digits):
        raise UserError(f"'{digits}' is not a time; type numbers only, like 830 or 1730")
    hour, minute = (int(digits[:-2]), int(digits[-2:])) if len(digits) > 2 else (int(digits), 0)
    if hour > 23 or minute > 59:
        raise UserError(f"'{digits}' is not a time of day; type it like 830 or 1730")
    return time(hour, minute)


def minutes_number(text: str) -> int:
    digits = text.strip()
    if not DIGITS.fullmatch(digits) or not 0 < int(digits) <= LONGEST_LUNCH:
        raise UserError(f"'{digits}' is not a number of minutes from 1 to {LONGEST_LUNCH}")
    return int(digits)


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
