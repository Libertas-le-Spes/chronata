from dataclasses import dataclass
from datetime import datetime, timedelta

from chronata.timekeeping.shifts.shifts import Shift
from chronata.use_cases.reminders.reminder_pace import ON_A_DAY_OFF, ReminderPace
from chronata.use_cases.reminders.reminder_setting import ClockOutReminderSetting
from chronata.use_cases.reminders.situation import Nudge, Situation


@dataclass(frozen=True)
class AfterTheShift:
    shift_end: datetime
    every: timedelta

    def first_due(self, current: Shift) -> datetime:
        if current.since < self.shift_end:
            return self.shift_end
        return current.since + self.every

    def nudge(self, situation: Situation, current: Shift) -> Nudge:
        return Nudge(f"Your shift ended at {self.shift_end:%H:%M}", f"Still working? Clocked in since {current.start:%H:%M}. Click to clock out now.",
                     situation.actions.clock_out(None, "clocked out from the reminder"), "Clock out now")


@dataclass(frozen=True)
class OnADayOff:
    every: timedelta = ON_A_DAY_OFF

    def first_due(self, current: Shift) -> datetime:
        return current.since + self.every

    def nudge(self, situation: Situation, current: Shift) -> Nudge:
        return Nudge("Still working on your day off?", f"Clocked in since {current.start:%a %H:%M}. Click to clock out now.",
                     situation.actions.clock_out(None, "clocked out from the reminder"), "Clock out now")


class ClockOut:
    def __init__(self, setting: ClockOutReminderSetting):
        self.setting = setting
        self.last_sent: dict[int, datetime] = {}

    def due(self, situation: Situation) -> Nudge | None:
        current = situation.current
        if current is None:
            return None
        schedule = schedule_for(situation, current, self.setting.current())
        if schedule is None:
            return None
        if situation.now < self._next(schedule, current):
            return None
        self.last_sent[current.id] = situation.now
        return schedule.nudge(situation, current)

    def _next(self, schedule: AfterTheShift | OnADayOff, current: Shift) -> datetime:
        sent = self.last_sent.get(current.id)
        if sent is None or sent < current.since:
            return schedule.first_due(current)
        return sent + schedule.every


def schedule_for(situation: Situation, current: Shift, pace: ReminderPace) -> AfterTheShift | OnADayOff | None:
    if pace.off:
        return None
    working_day = situation.hours.for_label(current.label)
    if working_day is None:
        return None
    started = current.start.date()
    if started.weekday() not in working_day.workdays:
        return OnADayOff()
    return AfterTheShift(datetime.combine(started, working_day.shift_end, current.start.tzinfo), pace.every)
