from chronata.presenters.page.facts import PageFacts
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.working_day import WEEKDAY_NAMES, WorkingDay
from chronata.use_cases.questions import typed_input


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
        "lunch": _lunch(main) if main else "",
        "shift": _shift(main) if main else typed_input.DEFAULT_SHIFT,
        "lunchQuestion": f"{typed_input.LUNCH_QUESTION} (leave empty for no lunch)",
        "shiftQuestion": typed_input.SHIFT_QUESTION,
        "defaultLabel": label_hours.default_label,
        "defaultLabelQuestion": typed_input.DEFAULT_LABEL_QUESTION,
    }


def _hours_of(label: str, hours: WorkingDay | None, default_label: str) -> dict:
    described = {"label": label, "isDefault": label == default_label, "setHours": hours is not None}
    if hours is None:
        return {**described, "shift": "", "lunch": "", "dailyHours": None, "weeklyHours": None, "daysOff": []}
    return {**described, "shift": _shift(hours), "lunch": _lunch(hours), "dailyHours": hours.daily_hours, "weeklyHours": hours.weekly_hours,
            "daysOff": [WEEKDAY_NAMES[day] for day in range(7) if day not in hours.workdays]}


def _shift(hours: WorkingDay) -> str:
    return f"{hours.shift_start:%H:%M} to {hours.shift_end:%H:%M}"


def _lunch(hours: WorkingDay) -> str:
    return f"{hours.lunch.start:%H:%M} for {hours.lunch.minutes} min" if hours.lunch else ""
