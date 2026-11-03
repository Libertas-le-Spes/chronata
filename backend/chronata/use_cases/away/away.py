from dataclasses import replace
from datetime import datetime, timedelta

from chronata.timekeeping.shifts.shifts import Shift, open_shift
from chronata.use_cases.away.away_stretch import AwayStore, AwayStretch
from chronata.use_cases.log.log import Log

LONG_ENOUGH_TO_ASK = timedelta(minutes=10)


class Away:
    def __init__(self, log: Log, store: AwayStore):
        self.log = log
        self.store = store

    def began(self, idle_seconds: int) -> None:
        current = open_shift(self.log.shifts())
        if current is None:
            return
        kept = self.store.load()
        if _still_away_on(kept, current):
            return
        since = max(self.log.clock() - timedelta(seconds=max(idle_seconds, 0)), current.since)
        self.store.keep(AwayStretch(current.id, since))

    def ended(self) -> None:
        kept = self.store.load()
        if kept is None or kept.back is not None:
            return
        self.store.keep(replace(kept, back=self.log.clock()))

    def to_ask_about(self) -> AwayStretch | None:
        kept = self.store.load()
        current = open_shift(self.log.shifts())
        if kept is None or current is None or kept.shift != current.id:
            return None
        now = self.log.clock()
        if kept.length(now) < LONG_ENOUGH_TO_ASK:
            return None
        if not self._past_the_shift(current, kept.until(now)):
            return None
        return AwayStretch(kept.shift, kept.since, kept.until(now))

    def settled(self) -> None:
        self.store.forget()

    def _past_the_shift(self, current: Shift, back: datetime) -> bool:
        working_day = self.log.hours.for_label(current.label)
        if working_day is None:
            return True
        started = current.start.date()
        if started.weekday() not in working_day.workdays:
            return True
        return back > datetime.combine(started, working_day.shift_end, current.start.tzinfo)


def _still_away_on(kept: AwayStretch | None, current: Shift) -> bool:
    if kept is None or kept.shift != current.id:
        return False
    return kept.back is None
