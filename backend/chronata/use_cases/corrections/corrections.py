from datetime import datetime

from chronata.timekeeping.entries.corrections import BreakExplained, ShiftAdded, ShiftCorrected, ShiftVoided
from chronata.timekeeping.shifts.durations import hours
from chronata.timekeeping.shifts.shifts import Shift, named
from chronata.timekeeping.shifts.start_answer import StartAnswer
from chronata.use_cases.labels.labelling import Labelling
from chronata.use_cases.log.log import Log, one_writer_at_a_time
from chronata.use_cases.log.outcome import Outcome, UserError
from chronata.use_cases.questions import typed_input
from chronata.use_cases.questions.questions import Answers
from chronata.use_cases.questions.start_questions import start_answer


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
        all_shifts = self.log.shifts()
        label = self.labels.settle(label, self.labels.in_use(all_shifts), answers, needs_hours=True)
        answered = start_answer(self.log.hours, label, begins, all_shifts, answers)
        added = ShiftAdded(begins, ends, typed_input.required(reason), label, note, answered)
        return self.log.write(added, f"added {begins:%Y-%m-%d %H:%M:%S} to {ends:%H:%M:%S}, worked {hours(ends - begins)}", now)

    @one_writer_at_a_time
    def correct(self, shift_ids: list[int], start: str | None, end: str | None, reason: str, answers: Answers = Answers()) -> Outcome:
        now = self.log.clock()
        pieces = self.log.shifts_with(shift_ids)
        begins, ends = _new_day(pieces, start, end, now)
        spans = _new_spans(pieces[0], pieces[-1], begins, ends)
        if any(span_start >= span_end for span_start, span_end in spans.values()):
            raise UserError("a shift has to end after it starts")
        written = typed_input.required(reason)
        first_answer = self._first_answer(pieces, begins, answers)
        changed = _changed(pieces, spans, written, first_answer)
        if not changed:
            raise UserError("those are already the times on record")
        for correction in changed:
            self.log.append(correction, now)
        return self.log.commit(f"corrected {named(pieces)} to {begins:%Y-%m-%d %H:%M:%S} to {ends:%H:%M:%S}")

    def _first_answer(self, pieces: list[Shift], begins: datetime, answers: Answers) -> StartAnswer:
        first = pieces[0]
        if begins == first.start:
            return first.start_answer
        others = _apart_from(self.log.shifts(), pieces)
        return start_answer(self.log.hours, first.label, begins, others, answers)

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


def _changed(pieces: list[Shift], spans: dict[int, tuple[datetime, datetime]], reason: str, first_answer: StartAnswer) -> list[ShiftCorrected]:
    changed = []
    for shift in pieces:
        if _moved(shift, spans):
            new_start, new_end = spans[shift.id]
            changed.append(ShiftCorrected(shift.id, new_start, new_end, reason, _answer_for(shift, pieces[0], first_answer)))
    return changed


def _moved(shift: Shift, spans: dict[int, tuple[datetime, datetime]]) -> bool:
    if shift.id not in spans:
        return False
    return spans[shift.id] != (shift.start, shift.end)


def _answer_for(shift: Shift, first: Shift, first_answer: StartAnswer) -> StartAnswer:
    if shift is first:
        return first_answer
    return shift.start_answer


def _apart_from(all_shifts: list[Shift], pieces: list[Shift]) -> list[Shift]:
    others = []
    for shift in all_shifts:
        if shift not in pieces:
            others.append(shift)
    return others


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
