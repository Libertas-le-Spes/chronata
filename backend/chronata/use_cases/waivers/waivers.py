from dataclasses import dataclass
from datetime import datetime, timedelta

from chronata.timekeeping.entries.waivers import TimeWaived, WaiverWithdrawn
from chronata.timekeeping.shifts.durations import hours
from chronata.timekeeping.shifts.shifts import Shift
from chronata.use_cases.log.log import Log, one_writer_at_a_time
from chronata.use_cases.log.outcome import Outcome, UserError
from chronata.use_cases.questions import typed_input


class Waivers:
    def __init__(self, log: Log):
        self.log = log

    @one_writer_at_a_time
    def waive(self, shift_ids: list[int], start: str, end: str, reason: str) -> Outcome:
        now = self.log.clock()
        written = typed_input.required(reason)
        stretch = _stretch_in(self.log.shifts_with(shift_ids), start, end, now)
        _refuse_overlap(stretch)
        message = f"waived {stretch.begins:%Y-%m-%d %H:%M:%S} to {stretch.ends:%H:%M:%S}, {hours(stretch.length)} no longer counted"
        return self.log.write(TimeWaived(stretch.shift.id, stretch.begins, stretch.ends, written), message, now)

    @one_writer_at_a_time
    def withdraw(self, shift_id: int, start: str, reason: str) -> Outcome:
        now = self.log.clock()
        written = typed_input.required(reason)
        shift = self.log.shift(shift_id)
        gap = shift.waived_from(_moment_from(start))
        if gap is None:
            raise UserError(f"shift {shift_id} has no waiver starting at {start}")
        message = f"took back the waiver for {gap.start:%Y-%m-%d %H:%M:%S} to {gap.end:%H:%M:%S}, {hours(gap.end - gap.start)} counted again"
        return self.log.write(WaiverWithdrawn(shift.id, gap.start, written), message, now)


@dataclass(frozen=True)
class Stretch:
    shift: Shift
    begins: datetime
    ends: datetime

    @property
    def length(self) -> timedelta:
        return self.ends - self.begins


def _stretch_in(pieces: list[Shift], start: str, end: str, now: datetime) -> Stretch:
    for shift in pieces:
        stretch = _read_on(shift, start, end, now)
        if stretch.length > timedelta() and _covers(stretch, now):
            return stretch
    return _refused(_read_on(pieces[0], start, end, now), now)


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


def _refuse_overlap(stretch: Stretch) -> None:
    for gap in stretch.shift.breaks:
        if gap.overlaps(stretch.begins, stretch.ends):
            raise UserError(f"{stretch.begins:%H:%M:%S} to {stretch.ends:%H:%M:%S} overlaps time already not counted, from {gap.start:%H:%M:%S} to {gap.end:%H:%M:%S}")


def _moment_from(text: str) -> datetime:
    try:
        return datetime.fromisoformat(text)
    except (TypeError, ValueError):
        raise UserError(f"'{text}' is not a waiver start as shown on the record")
