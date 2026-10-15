from chronata.timekeeping.entries.compensation import Compensated
from chronata.use_cases import typed_input
from chronata.use_cases.labelling import Labelling
from chronata.use_cases.log import Log, one_writer_at_a_time
from chronata.use_cases.outcome import Outcome, UserError


class Compensations:
    def __init__(self, log: Log, labels: Labelling):
        self.log = log
        self.labels = labels

    @one_writer_at_a_time
    def record(self, label: str, start: str, end: str, hours: float, time_off: bool, reference: str | None, new_label: bool = False) -> Outcome:
        begins, ends = typed_input.day(start), typed_input.day(end)
        if ends < begins:
            raise UserError("the period ends before it starts")
        if hours < 0:
            raise UserError("hours compensated cannot be negative")
        chosen = self.labels.settle(label, new_label, self.labels.in_use(self.log.shifts()), needs_hours=True) or self.log.hours.default_label
        given = "given as time off" if time_off else "paid"
        message = f"recorded {hours:g}h of {chosen + ' ' if chosen else ''}overtime {given} for {begins} to {ends}"
        return self.log.write(Compensated(begins, ends, hours, time_off, reference or "", chosen), message, self.log.clock())
