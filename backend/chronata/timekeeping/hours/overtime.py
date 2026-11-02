from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable

from chronata.timekeeping.shifts.durations import NONE


@dataclass(frozen=True)
class Overtime:
    earned: timedelta = NONE

    @property
    def earned_some(self) -> bool:
        return self.earned > NONE

    def __add__(self, other: "Overtime") -> "Overtime":
        return Overtime(self.earned + other.earned)


def beyond(worked: timedelta, normal: timedelta) -> Overtime:
    return Overtime(worked - normal)


def total(overtimes: Iterable[Overtime]) -> Overtime:
    return sum(overtimes, Overtime())
