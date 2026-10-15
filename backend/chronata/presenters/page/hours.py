from dataclasses import asdict

from chronata.presenters.page.facts import PageFacts
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.working_day import WEEKDAY_NAMES, WorkingDay
from chronata.use_cases.questions import typed_input
from chronata.use_cases.questions.questions import HOURS_INPUTS, filled_in, hours_values


def state(facts: PageFacts) -> dict:
    label_hours = facts.hours
    return {
        "setup": _setup(label_hours),
        "labelHours": [_hours_of(label, label_hours.for_label(label), label_hours.default_label) for label in label_hours.labels()],
    }


def _setup(label_hours: LabelHours) -> dict:
    main = label_hours.main
    return {
        "needed": not label_hours.configured,
        "hoursInputs": _inputs(main),
        "defaultLabel": label_hours.default_label,
        "defaultLabelQuestion": typed_input.DEFAULT_LABEL_QUESTION,
    }


def _hours_of(label: str, hours: WorkingDay | None, default_label: str) -> dict:
    described = {"label": label, "isDefault": label == default_label, "setHours": hours is not None, "hoursInputs": _inputs(hours)}
    if hours is None:
        return {**described, "shift": "", "lunch": "", "dailyHours": None, "weeklyHours": None, "daysOff": []}
    return {**described, "shift": _shift(hours), "lunch": _lunch(hours), "dailyHours": hours.daily_hours, "weeklyHours": hours.weekly_hours,
            "daysOff": [WEEKDAY_NAMES[day] for day in range(7) if day not in hours.workdays]}


def _inputs(hours: WorkingDay | None) -> list[dict]:
    return [asdict(needed) for needed in filled_in(HOURS_INPUTS, hours_values(hours))]


def _shift(hours: WorkingDay) -> str:
    return f"{hours.shift_start:%H:%M} to {hours.shift_end:%H:%M}"


def _lunch(hours: WorkingDay) -> str:
    return f"{hours.lunch.start:%H:%M} for {hours.lunch.minutes} min" if hours.lunch else ""
