from dataclasses import dataclass
from datetime import timedelta
from typing import ClassVar

from chronata.timekeeping.shifts.durations import NONE


@dataclass(frozen=True)
class TimeOff:
    kind: ClassVar[str] = "time_off"
    wording: ClassVar[str] = "given as time off"
    hours: float
    reference: str = ""

    @property
    def paid(self) -> timedelta:
        return NONE

    @property
    def time_off(self) -> timedelta:
        return timedelta(hours=self.hours)
