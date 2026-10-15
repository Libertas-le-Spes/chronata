from datetime import date, datetime, timedelta

from chronata.use_cases.reminders.situation import Nudge, Situation

REMINDER_HOURS = range(7, 18)
BETWEEN_REMINDERS = timedelta(hours=1)
REMINDERS_PER_DAY = 2
LONG_SHIFT = timedelta(hours=12)


class LunchTime:
    def __init__(self):
        self.asked: set[date] = set()

    def due(self, situation: Situation) -> Nudge | None:
        if not _at_lunch(situation) or situation.now.date() in self.asked:
            return None
        self.asked.add(situation.now.date())
        return Nudge("Lunch time", "Clocking out for lunch? Ignore this if you're working through it.",
                     situation.actions.clock_out(None, "lunch"), "Clock out for lunch")


class LongShift:
    def __init__(self):
        self.warned: set[int] = set()

    def due(self, situation: Situation) -> Nudge | None:
        current = situation.current
        if not _clocked_in_long(situation) or current.id in self.warned:
            return None
        self.warned.add(current.id)
        return Nudge("Still working?", f"Clocked in since {current.start:%H:%M}. Click to open the log.", situation.actions.open())


class LunchOver:
    def __init__(self):
        self.asked: set[date] = set()

    def due(self, situation: Situation) -> Nudge | None:
        if not _back_from_lunch_time(situation) or situation.now.date() in self.asked:
            return None
        self.asked.add(situation.now.date())
        return Nudge("Lunch is over", "Clocking back in?", situation.actions.clock_in("back from lunch"), "Clock back in")



class NotClockedIn:
    def __init__(self):
        self.sent: dict[date, list[datetime]] = {}

    def due(self, situation: Situation) -> Nudge | None:
        if not _nothing_clocked_yet_today(situation) or not self._room_for_one(situation.now):
            return None
        self.sent.setdefault(situation.now.date(), []).append(situation.now)
        clock_in = situation.actions.clock_in("clocked in from the reminder")
        if situation.hours.is_workday(situation.now):
            return Nudge("Not clocked in", "If you've started work, click to clock in now.", clock_in, "Clock in")
        return Nudge(f"It's {situation.now:%A}. Working today?", "Your PC is on. If you're working, click to clock in now.", clock_in, "Clock in")

    def _room_for_one(self, now: datetime) -> bool:
        sent = self.sent.get(now.date(), [])
        if len(sent) >= REMINDERS_PER_DAY:
            return False
        return not sent or now - sent[-1] >= BETWEEN_REMINDERS


def _at_lunch(situation: Situation) -> bool:
    lunch = situation.lunch_of(situation.current.label) if situation.current else None
    return lunch is not None and lunch[0] <= situation.now < lunch[1]


def _clocked_in_long(situation: Situation) -> bool:
    return situation.current is not None and situation.now - situation.current.since >= LONG_SHIFT


def _back_from_lunch_time(situation: Situation) -> bool:
    if situation.current is not None:
        return False
    lunch = _lunch_clocked_out_for(situation)
    return lunch is not None and situation.now >= lunch[1]


def _lunch_clocked_out_for(situation: Situation) -> tuple[datetime, datetime] | None:
    lunches = [(shift, situation.lunch_of(shift.label)) for shift in situation.finished_today]
    taken = [lunch for shift, lunch in lunches if lunch and lunch[0] <= shift.end < lunch[1]]
    return taken[-1] if taken else None


def _nothing_clocked_yet_today(situation: Situation) -> bool:
    nothing_yet = situation.current is None and not situation.finished_today
    return nothing_yet and situation.now.hour in REMINDER_HOURS
