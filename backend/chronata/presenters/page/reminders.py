from chronata.presenters.page.facts import PageFacts
from chronata.timekeeping.shifts.durations import minutes


def state(facts: PageFacts) -> dict:
    return {"reminders": {"clockOutEvery": _every(facts)}}


def _every(facts: PageFacts) -> int | None:
    pace = facts.reminder_pace
    if pace.off:
        return None
    return minutes(pace.every)
