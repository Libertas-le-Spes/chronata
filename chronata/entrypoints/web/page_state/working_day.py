from chronata.entrypoints.web.page_state.snapshot import Snapshot
from chronata.timekeeping.working_day import WEEKDAY_NAMES
from chronata.use_cases import typed_input


def state(app, taken: Snapshot) -> dict:
    working_day = taken.working_day
    return {
        "setup": {
            "needed": not working_day.configured,
            "lunch": f"{working_day.lunch_start:%H:%M} for {working_day.lunch_minutes} min",
            "shift": f"{working_day.shift_start:%H:%M} to {working_day.shift_end:%H:%M}",
            "lunchQuestion": typed_input.LUNCH_QUESTION,
            "shiftQuestion": typed_input.SHIFT_QUESTION,
            "defaultLabel": working_day.default_label,
            "defaultLabelQuestion": typed_input.DEFAULT_LABEL_QUESTION,
        },
        "workingDay": {
            "dailyHours": working_day.daily_hours,
            "weeklyHours": working_day.weekly_hours,
            "daysOff": [WEEKDAY_NAMES[day] for day in range(7) if day not in working_day.workdays],
        },
    }
