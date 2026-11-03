from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from chronata.timekeeping.shifts.shifts import Shift, open_shift
from chronata.use_cases.away.away_stretch import AwayStore, AwayStretch
from chronata.use_cases.away.occasions import occasion_of
from chronata.use_cases.log.log import Log

LONG_ENOUGH_TO_ASK = timedelta(minutes=10)


@dataclass(frozen=True)
class TimeAway:
    stretch: AwayStretch
    occasion: str
    clocked_in_since: datetime

    @property
    def left_after_clocking_in(self) -> bool:
        return self.stretch.since > self.clocked_in_since


class Away:
    def __init__(self, log: Log, store: AwayStore):
        self.log = log
        self.store = store

    def began(self, idle_seconds: int) -> None:
        current = open_shift(self.log.shifts())
        if current is None:
            return
        input_stopped = self.log.clock() - timedelta(seconds=idle_seconds)
        self.store.keep(AwayStretch(current.id, max(input_stopped, current.since)))

    def ended(self) -> None:
        kept = self.store.load()
        if kept is None or kept.back is not None:
            return
        self.store.keep(replace(kept, back=self.log.clock()))

    def to_ask_about(self) -> TimeAway | None:
        kept = self.store.load()
        current = open_shift(self.log.shifts())
        if kept is None or current is None or kept.shift != current.id:
            return None
        now = self.log.clock()
        if kept.length(now) < LONG_ENOUGH_TO_ASK:
            return None
        occasion = occasion_of(self.log.hours, current)
        if not occasion.reached_by(kept.until(now)):
            return None
        return TimeAway(AwayStretch(kept.shift, kept.since, kept.until(now)), occasion.wording, current.since)

    def settled(self) -> None:
        self.store.forget()
