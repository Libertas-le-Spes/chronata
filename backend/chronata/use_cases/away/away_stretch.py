from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol


@dataclass(frozen=True)
class AwayStretch:
    shift: int
    since: datetime
    back: datetime | None = None

    def until(self, now: datetime) -> datetime:
        if self.back is None:
            return now
        return self.back

    def length(self, now: datetime) -> timedelta:
        return self.until(now) - self.since


class AwayStore(Protocol):
    def load(self) -> AwayStretch | None: ...
    def keep(self, stretch: AwayStretch) -> None: ...
    def forget(self) -> None: ...
