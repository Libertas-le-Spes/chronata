from datetime import datetime

from chronata.timekeeping.entries.corrections import BreakExplained, ShiftAdded, ShiftCorrected, ShiftVoided
from chronata.timekeeping.shifts.durations import hours
from chronata.timekeeping.shifts.shifts import Shift, named
from chronata.use_cases.labels.labelling import Labelling
from chronata.use_cases.log.log import Log, one_writer_at_a_time
from chronata.use_cases.log.outcome import Outcome, UserError
from chronata.use_cases.questions import typed_input
from chronata.use_cases.questions.questions import Answers


class Corrections:
    def __init__(self, log: Log, labels: Labelling):
        self.log = log
        self.labels = labels

    @one_writer_at_a_time
    def add(self, day: str, start: str, end: str, reason: str, note: str | None, label: str = "", answers: Answers = Answers()) -> Outcome:
        now = self.log.clock()
        begins = typed_input.moment(start, typed_input.day(day), now)
        ends = typed_input.end_after(begins, end, now)
        if ends > now:
            raise UserError("that shift has not ended yet; clock in instead")
        label = self.labels.settle(label, self.labels.in_use(self.log.shifts()), answers, needs_hours=True)
        added = ShiftAdded(begins, ends, typed_input.required(reason), label, note)
        return self.log.write(added, f"added {begins:%Y-%m-%d %H:%M:%S} to {ends:%H:%M:%S}, worked {hours(ends - begins)}", now)

    @one_writer_at_a_time
    def correct(self, shift_ids: list[int], start: str | None, end: str | None, reason: str) -> Outcome:
        now = self.log.clock()
        pieces = self.log.shifts_with(shift_ids)
        begins, ends = _new_day(pieces, start, end, now)
        spans = _new_spans(pieces[0], pieces[-1], begins, ends)
        if any(span_start >= span_end for span_start, span_end in spans.values()):
            raise UserError("a shift has to end after it starts")
        written = typed_input.required(reason)
        recorded = {shift.id: (shift.start, shift.end) for shift in pieces}
        changed = [ShiftCorrected(shift_id, *span, written) for shift_id, span in spans.items() if span != recorded[shift_id]]
        if not changed:
            raise UserError("those are already the times on record")
        for correction in changed:
            self.log.append(correction, now)
        return self.log.commit(f"corrected {named(pieces)} to {begins:%Y-%m-%d %H:%M:%S} to {ends:%H:%M:%S}")

    @one_writer_at_a_time
    def mark_mistake(self, shift_ids: list[int], reason: str) -> Outcome:
        written = typed_input.required(reason)
        chosen = self.log.shifts_with(shift_ids)
        marking = [shift for shift in chosen if not shift.voided]
        if not marking:
            raise UserError(f"{named(chosen)} already marked as a mistake")
        now = self.log.clock()
        for shift in marking:
            self.log.append(ShiftVoided(shift.id, written), now)
        return self.log.commit(f"marked {named(marking)} as a mistake")

    @one_writer_at_a_time
    def explain_break(self, shift_id: int, start: str, reason: str) -> Outcome:
        shift = self.log.shift(shift_id)
        gap = next((b for b in shift.breaks if b.start.isoformat() == start), None)
        if gap is None:
            raise UserError(f"shift {shift_id} has no break starting at {start}")
        message = f"noted why the PC was off from {gap.start:%H:%M}: {typed_input.required(reason)}"
        return self.log.write(BreakExplained(shift.id, start, reason.strip()), message, self.log.clock())


def _new_day(pieces: list[Shift], start: str | None, end: str | None, now: datetime) -> tuple[datetime, datetime]:
    first, last = pieces[0], pieces[-1]
    if last.end is None:
        raise UserError("clock out before correcting")
    begins = typed_input.moment(start, first.start.date(), now) if start else first.start
    ends = typed_input.end_after(begins, end, now) if end else last.end
    if ends > now:
        raise UserError("a shift cannot end in the future")
    return begins, ends


def _new_spans(first: Shift, last: Shift, begins: datetime, ends: datetime) -> dict[int, tuple[datetime, datetime]]:
    if first is last:
        return {first.id: (begins, ends)}
    return {first.id: (begins, first.end), last.id: (last.start, ends)}
