from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

EVERY_HALF_HOUR = timedelta(minutes=30)
ON_A_DAY_OFF = timedelta(hours=1)


@dataclass(frozen=True)
class ReminderPace:
    every: timedelta | None = EVERY_HALF_HOUR

    @property
    def off(self) -> bool:
        return self.every is None


class ReminderPaceStore(Protocol):
    def load(self) -> ReminderPace: ...
    def save(self, pace: ReminderPace) -> None: ...
