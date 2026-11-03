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
        pieces = self.log.shifts_with(shift_ids)
        begins = _waived_from(start, pieces[0], now)
        ends = typed_input.end_after(begins, end, now)
        if ends > now:
            raise UserError("a waived stretch cannot end in the future")
        shift = _clocked_through(pieces, begins, ends, now)
        _refuse_overlap(shift, begins, ends)
        message = f"waived {begins:%Y-%m-%d %H:%M:%S} to {ends:%H:%M:%S}, {hours(ends - begins)} no longer counted"
        return self.log.write(TimeWaived(shift.id, begins, ends, written), message, now)

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


def _waived_from(start: str, first: Shift, now: datetime) -> datetime:
    begins = typed_input.moment(start, first.start.date(), now, allow_future=True)
    if begins >= first.start or not typed_input.time_only(start):
        return begins
    if _clocked_until(first, now).date() == first.start.date():
        return begins
    return begins + timedelta(days=1)


def _clocked_through(pieces: list[Shift], begins: datetime, ends: datetime, now: datetime) -> Shift:
    for shift in pieces:
        if _covers(shift, begins, ends, now):
            return shift
    raise UserError(f"{begins:%H:%M:%S} to {ends:%H:%M:%S} is not inside one clocked shift")


def _covers(shift: Shift, begins: datetime, ends: datetime, now: datetime) -> bool:
    if shift.voided:
        return False
    if begins < shift.start:
        return False
    return ends <= _clocked_until(shift, now)


def _clocked_until(shift: Shift, now: datetime) -> datetime:
    if shift.end is None:
        return now
    return shift.end


def _refuse_overlap(shift: Shift, begins: datetime, ends: datetime) -> None:
    for gap in shift.breaks:
        if gap.overlaps(begins, ends):
            raise UserError(f"{begins:%H:%M:%S} to {ends:%H:%M:%S} overlaps time already not counted, from {gap.start:%H:%M:%S} to {gap.end:%H:%M:%S}")


def _moment_from(text: str) -> datetime:
    try:
        return datetime.fromisoformat(text)
    except (TypeError, ValueError):
        raise UserError(f"'{text}' is not a waiver start as shown on the record")
