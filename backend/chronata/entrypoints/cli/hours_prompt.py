from datetime import time
from typing import Callable

from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions import typed_input

Ask = Callable[[str], str]


def ask_hours(ask: Ask, current: WorkingDay | None) -> tuple[str, str]:
    start = _time(ask, "Shift starts at", current.shift_start if current else None, "830")
    end = _time(ask, "Shift ends at", current.shift_end if current else None, "1730")
    shift = f"{start:%H:%M} to {end:%H:%M}"
    lunch_start = _asked(ask, "Lunch starts at (e.g. 1200, Enter for no lunch): ", _optional_time)
    if lunch_start is None:
        return shift, ""
    minutes = _asked(ask, "Lunch in minutes (e.g. 45, Enter for no lunch): ", _optional_minutes)
    return shift, f"{lunch_start:%H:%M} for {minutes} min" if minutes else ""


def _time(ask: Ask, question: str, current: time | None, example: str) -> time:
    shown = f"[{current:%H%M}]" if current else f"(e.g. {example})"
    return _asked(ask, f"{question} {shown}: ", lambda text: current if not text and current else typed_input.clock_number(text))


def _optional_time(text: str) -> time | None:
    return typed_input.clock_number(text) if text else None


def _optional_minutes(text: str) -> int:
    return typed_input.minutes_number(text) if text else 0


def _asked(ask: Ask, prompt: str, read: Callable):
    while True:
        try:
            return read(ask(prompt).strip())
        except UserError as error:
            print(f"  {error}")
