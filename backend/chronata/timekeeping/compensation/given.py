from dataclasses import dataclass
from datetime import timedelta
from typing import ClassVar

from chronata.timekeeping.hours.overtime import NONE


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


Given = Payment | TimeOff
GIVEN_AS = {kind.kind: kind for kind in (Payment, TimeOff)}
GIVEN_AS_TIME_OFF = {True: TimeOff, False: Payment}


def given_in(data: dict) -> Given:
    return GIVEN_AS[data["kind"]](data["hours"], data.get("reference", ""))
