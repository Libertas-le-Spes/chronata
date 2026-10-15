from chronata.entrypoints.web.page_state.snapshot import Snapshot
from chronata.timekeeping.working_day import WEEKDAY_NAMES, WorkingDay
from chronata.use_cases import typed_input


def state(app, taken: Snapshot) -> dict:
    label_hours = taken.hours
    main = label_hours.main
    return {
        "setup": {
            "needed": not label_hours.configured,
            "lunch": _lunch(main) if main else "",
            "shift": _shift(main) if main else typed_input.DEFAULT_SHIFT,
            "lunchQuestion": typed_input.LUNCH_QUESTION,
            "shiftQuestion": typed_input.SHIFT_QUESTION,
            "defaultLabel": label_hours.default_label,
            "defaultLabelQuestion": typed_input.DEFAULT_LABEL_QUESTION,
        },
        "labelHours": [
            {"label": label, "isDefault": label == label_hours.default_label, "setHours": hours is not None,
             "shift": _shift(hours) if hours else "", "lunch": _lunch(hours) if hours else "",
             "dailyHours": hours.daily_hours if hours else None, "weeklyHours": hours.weekly_hours if hours else None,
             "daysOff": [WEEKDAY_NAMES[day] for day in range(7) if day not in hours.workdays] if hours else []}
            for label in label_hours.labels() for hours in [label_hours.for_label(label)]
        ],
    }


def _shift(hours: WorkingDay) -> str:
    return f"{hours.shift_start:%H:%M} to {hours.shift_end:%H:%M}"


def _lunch(hours: WorkingDay) -> str:
    return f"{hours.lunch.start:%H:%M} for {hours.lunch.minutes} min" if hours.lunch else ""
