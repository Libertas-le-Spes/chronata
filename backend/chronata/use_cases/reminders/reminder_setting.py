from datetime import timedelta

from chronata.use_cases.log.outcome import Outcome, UserError
from chronata.use_cases.reminders.reminder_pace import FEWEST_MINUTES, MOST_MINUTES, ReminderPace, ReminderPaceStore, allowed_minutes


class ClockOutReminderSetting:
    def __init__(self, store: ReminderPaceStore):
        self.store = store

    def current(self) -> ReminderPace:
        return self.store.load()

    def remind_every(self, minutes: int) -> Outcome:
        if not isinstance(minutes, int):
            raise UserError("say how many minutes, as a whole number")
        if not allowed_minutes(minutes):
            raise UserError(f"choose between {FEWEST_MINUTES} and {MOST_MINUTES} minutes")
        self.store.save(ReminderPace(timedelta(minutes=minutes)))
        return Outcome(f"after your shift ends, you are reminded to clock out every {minutes} minutes", None)

    def turn_off(self) -> Outcome:
        self.store.save(ReminderPace(None))
        return Outcome("clock-out reminders are off", None)
