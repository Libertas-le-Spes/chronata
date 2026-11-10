from datetime import datetime, timedelta

from chronata.timekeeping.entries.waivers import TimeWaived, WaiverWithdrawn
from chronata.timekeeping.hours.lateness_made_up import lateness_made_up_by
from chronata.use_cases.log.log import Log, one_writer_at_a_time
from chronata.use_cases.log.outcome import Outcome, UserError
from chronata.use_cases.questions import typed_input
from chronata.use_cases.waivers import waiver_messages
from chronata.use_cases.waivers.kept_for_lateness import kept_for_lateness, waived_pieces
from chronata.use_cases.waivers.stretch import Stretch
from chronata.use_cases.waivers.typed_stretch import refuse_overlap, stretch_in


class Waivers:
    def __init__(self, log: Log):
        self.log = log

    @one_writer_at_a_time
    def waive(self, shift_ids: list[int], start: str, end: str, reason: str) -> Outcome:
        now = self.log.clock()
        written = typed_input.required(reason)
        asked = stretch_in(self.log.shifts_with(shift_ids), start, end, now)
        refuse_overlap(asked)
        kept = kept_for_lateness(asked, self._making_up_lateness(asked, written, now), self.log.hours)
        pieces = waived_pieces(asked, kept)
        if not pieces:
            return Outcome(waiver_messages.nothing_waived(asked), None)
        for piece in pieces:
            self.log.append(TimeWaived(piece.shift.id, piece.begins, piece.ends, written), now)
        return self.log.commit(waiver_messages.waived(pieces, kept))

    @one_writer_at_a_time
    def withdraw(self, shift_id: int, start: str, reason: str) -> Outcome:
        now = self.log.clock()
        written = typed_input.required(reason)
        shift = self.log.shift(shift_id)
        gap = shift.waived_from(_moment_from(start))
        if gap is None:
            raise UserError(f"shift {shift_id} has no waiver starting at {start}")
        return self.log.write(WaiverWithdrawn(shift.id, gap.start, written), waiver_messages.took_back(gap), now)

    def _making_up_lateness(self, stretch: Stretch, reason: str, now: datetime) -> timedelta:
        return lateness_made_up_by(stretch.waived(reason), stretch.shift, self.log.shifts(), self.log.hours, now)


def _moment_from(text: str) -> datetime:
    try:
        return datetime.fromisoformat(text)
    except (TypeError, ValueError):
        raise UserError(f"'{text}' is not a waiver start as shown on the record")
