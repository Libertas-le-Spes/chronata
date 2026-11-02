from datetime import timedelta
from typing import Protocol

from chronata.timekeeping.compensation.given_kinds.not_known import NotKnown
from chronata.timekeeping.compensation.given_kinds.payment import Payment
from chronata.timekeeping.compensation.given_kinds.time_off import TimeOff


class Given(Protocol):
    kind: str
    hours: float
    reference: str

    @property
    def paid(self) -> timedelta: ...

    @property
    def time_off(self) -> timedelta: ...


class Chosen(Given, Protocol):
    wording: str


GIVEN_AS: dict[str, type[Chosen]] = {kind.kind: kind for kind in (Payment, TimeOff)}


def given_in(data: dict) -> Given:
    reference = data.get("reference", "")
    kind = GIVEN_AS.get(data.get("kind"))
    if kind is None:
        return NotKnown(data.get("kind", ""), data.get("hours", 0), reference)
    return kind(data["hours"], reference)
