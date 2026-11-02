from dataclasses import dataclass
from datetime import timedelta
from typing import ClassVar

from chronata.timekeeping.shifts.durations import NONE


@dataclass(frozen=True)
class Payment:
    kind: ClassVar[str] = "paid"
    wording: ClassVar[str] = "paid"
    hours: float
    reference: str = ""

    @property
    def paid(self) -> timedelta:
        return timedelta(hours=self.hours)

    @property
    def time_off(self) -> timedelta:
        return NONE
