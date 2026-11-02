from dataclasses import dataclass
from datetime import timedelta

from chronata.timekeeping.shifts.durations import NONE


@dataclass(frozen=True)
class NotKnown:
    kind: str
    hours: float
    reference: str = ""

    @property
    def paid(self) -> timedelta:
        return NONE

    @property
    def time_off(self) -> timedelta:
        return NONE
