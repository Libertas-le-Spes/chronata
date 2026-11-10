from dataclasses import dataclass
from datetime import datetime, timedelta

from chronata.timekeeping.shifts.shifts import WAIVED, Break, Shift
from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions import typed_input


@dataclass(frozen=True)
class Stretch:
    shift: Shift
    begins: datetime
    ends: datetime

    @property
    def length(self) -> timedelta:
        return self.ends - self.begins

    def waived(self, reason: str) -> Break:
        return Break(self.begins, self.ends, WAIVED, reason)

    def after_the_first(self, kept: timedelta) -> "Stretch":
        return Stretch(self.shift, self.begins + kept, self.ends)


def stretch_in(pieces: list[Shift], start: str, end: str, now: datetime) -> Stretch:
    for shift in pieces:
        stretch = _read_on(shift, start, end, now)
        if stretch.length > timedelta() and _covers(stretch, now):
            return stretch
    return _refused(_read_on(pieces[0], start, end, now), now)


def refuse_overlap(stretch: Stretch) -> None:
    for gap in stretch.shift.breaks:
        if gap.overlaps(stretch.begins, stretch.ends):
            raise UserError(f"{stretch.begins:%H:%M:%S} to {stretch.ends:%H:%M:%S} overlaps time already not counted, from {gap.start:%H:%M:%S} to {gap.end:%H:%M:%S}")


def _read_on(shift: Shift, start: str, end: str, now: datetime) -> Stretch:
    begins = _waived_from(start, shift, now)
    return Stretch(shift, begins, typed_input.end_after(begins, end, now))


def _refused(stretch: Stretch, now: datetime) -> Stretch:
    if stretch.length <= timedelta():
        raise UserError("a waived stretch has to end after it starts")
    if stretch.ends > now:
        raise UserError("a waived stretch cannot end in the future")
    raise UserError(f"{stretch.begins:%H:%M:%S} to {stretch.ends:%H:%M:%S} is not inside one clocked shift")


def _waived_from(start: str, shift: Shift, now: datetime) -> datetime:
    begins = typed_input.moment(start, shift.start.date(), now, allow_future=True)
    if begins >= shift.start or not typed_input.time_only(start):
        return begins
    if _clocked_until(shift, now).date() == shift.start.date():
        return begins
    return begins + timedelta(days=1)


def _covers(stretch: Stretch, now: datetime) -> bool:
    shift = stretch.shift
    if shift.voided:
        return False
    if stretch.begins < shift.start:
        return False
    return stretch.ends <= _clocked_until(shift, now)


def _clocked_until(shift: Shift, now: datetime) -> datetime:
    if shift.end is None:
        return now
    return shift.end
