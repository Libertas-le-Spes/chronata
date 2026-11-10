from datetime import datetime, timedelta

from chronata.timekeeping.entries.waivers import TimeWaived, WaiverWithdrawn
from chronata.timekeeping.hours.lateness_made_up import lateness_made_up_by
from chronata.timekeeping.shifts.durations import NONE, hours
from chronata.use_cases.log.log import Log, one_writer_at_a_time
from chronata.use_cases.log.outcome import Outcome, UserError
from chronata.use_cases.questions import typed_input
from chronata.use_cases.waivers.stretch import Stretch, refuse_overlap, stretch_in


class Waivers:
    def __init__(self, log: Log):
        self.log = log

    @one_writer_at_a_time
    def waive(self, shift_ids: list[int], start: str, end: str, reason: str) -> Outcome:
        now = self.log.clock()
        written = typed_input.required(reason)
        asked = stretch_in(self.log.shifts_with(shift_ids), start, end, now)
        refuse_overlap(asked)
        kept = self._making_up_lateness(asked, written, now)
        if kept >= asked.length:
            return Outcome(f"nothing waived: {_span(asked)} makes up for coming in late, so it still counts", None)
        waived = asked.after_the_first(kept)
        message = f"waived {waived.begins:%Y-%m-%d %H:%M:%S} to {waived.ends:%H:%M:%S}, {hours(waived.length)} no longer counted{_kept(asked, kept)}"
        return self.log.write(TimeWaived(waived.shift.id, waived.begins, waived.ends, written), message, now)

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

    def _making_up_lateness(self, stretch: Stretch, reason: str, now: datetime) -> timedelta:
        return lateness_made_up_by(stretch.waived(reason), stretch.shift, self.log.shifts(), self.log.hours, now)


def _kept(asked: Stretch, kept: timedelta) -> str:
    if kept <= NONE:
        return ""
    made_up = Stretch(asked.shift, asked.begins, asked.begins + kept)
    return f"; kept {_span(made_up)} ({hours(kept)}), which makes up for coming in late"


def _span(stretch: Stretch) -> str:
    return f"{stretch.begins:%H:%M:%S} to {stretch.ends:%H:%M:%S}"


def _moment_from(text: str) -> datetime:
    try:
        return datetime.fromisoformat(text)
    except (TypeError, ValueError):
        raise UserError(f"'{text}' is not a waiver start as shown on the record")
