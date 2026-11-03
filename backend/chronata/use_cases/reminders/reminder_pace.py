from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

EVERY_HALF_HOUR = timedelta(minutes=30)
ON_A_DAY_OFF = timedelta(hours=1)
FEWEST_MINUTES = 5
MOST_MINUTES = 240


@dataclass(frozen=True)
class ReminderPace:
    every: timedelta | None = EVERY_HALF_HOUR

    @property
    def off(self) -> bool:
        return self.every is None


def allowed_minutes(minutes) -> bool:
    if not isinstance(minutes, int):
        return False
    return FEWEST_MINUTES <= minutes <= MOST_MINUTES


class ReminderPaceStore(Protocol):
    def load(self) -> ReminderPace: ...
    def save(self, pace: ReminderPace) -> None: ...
