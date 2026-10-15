from chronata.timekeeping.durations import hours
from chronata.timekeeping.entries.corrections import BreakExplained, ShiftAdded, ShiftCorrected, ShiftVoided
from chronata.use_cases import typed_input
from chronata.use_cases.labelling import Labelling
from chronata.use_cases.log import Log, one_writer_at_a_time
from chronata.use_cases.outcome import Outcome, UserError
from chronata.use_cases.questions import Answers


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
    def correct(self, shift_id: int, start: str | None, end: str | None, reason: str) -> Outcome:
        now = self.log.clock()
        shift = self.log.shift(shift_id)
        if shift.end is None:
            raise UserError("clock out of this shift before correcting it")
        begins = typed_input.moment(start, shift.start.date(), now) if start else shift.start
        ends = typed_input.end_after(begins, end, now) if end else shift.end
        if ends <= begins or ends > now:
            raise UserError("a shift has to end after it starts, and not in the future")
        corrected = ShiftCorrected(shift.id, begins, ends, typed_input.required(reason))
        return self.log.write(corrected, f"corrected shift {shift.id} to {begins:%Y-%m-%d %H:%M:%S} to {ends:%H:%M:%S}", now)

    @one_writer_at_a_time
    def strike(self, shift_id: int, reason: str) -> Outcome:
        shift = self.log.shift(shift_id)
        if shift.voided:
            raise UserError(f"shift {shift_id} is already struck out")
        return self.log.write(ShiftVoided(shift.id, typed_input.required(reason)), f"struck out shift {shift.id}", self.log.clock())

    @one_writer_at_a_time
    def explain_break(self, shift_id: int, start: str, reason: str) -> Outcome:
        shift = self.log.shift(shift_id)
        gap = next((b for b in shift.breaks if b.start.isoformat() == start), None)
        if gap is None:
            raise UserError(f"shift {shift_id} has no break starting at {start}")
        message = f"noted why the PC was off from {gap.start:%H:%M}: {typed_input.required(reason)}"
        return self.log.write(BreakExplained(shift.id, start, reason.strip()), message, self.log.clock())
