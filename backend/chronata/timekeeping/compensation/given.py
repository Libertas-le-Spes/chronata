from dataclasses import dataclass
from datetime import timedelta
from typing import ClassVar, Protocol

from chronata.timekeeping.shifts.durations import NONE


class Given(Protocol):
    kind: ClassVar[str]
    wording: ClassVar[str]
    hours: float
    reference: str

    @property
    def paid(self) -> timedelta: ...

    @property
    def time_off(self) -> timedelta: ...


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


@dataclass(frozen=True)
class NotKnown:
    kind: ClassVar[str] = "not known"
    wording: ClassVar[str] = "given in a way this version does not know"
    hours: float = 0
    reference: str = ""

    @property
    def paid(self) -> timedelta:
        return NONE

    @property
    def time_off(self) -> timedelta:
        return NONE


GIVEN_AS = {kind.kind: kind for kind in (Payment, TimeOff)}


def given_in(data: dict) -> Given:
    reference = data.get("reference", "")
    kind = GIVEN_AS.get(data.get("kind"))
    if kind is None:
        return NotKnown(reference=reference)
    return kind(data["hours"], reference)
