from chronata.timekeeping.compensation.given import GIVEN_AS_TIME_OFF
from chronata.timekeeping.entries.compensation import Compensated
from chronata.use_cases.labels.labelling import Labelling
from chronata.use_cases.log.log import Log, one_writer_at_a_time
from chronata.use_cases.log.outcome import Outcome, UserError
from chronata.use_cases.questions import typed_input
from chronata.use_cases.questions.questions import Answers


class Compensations:
    def __init__(self, log: Log, labels: Labelling):
        self.log = log
        self.labels = labels

    @one_writer_at_a_time
    def record(self, label: str, start: str, end: str, hours: float, time_off: bool, reference: str | None, answers: Answers = Answers()) -> Outcome:
        begins, ends = typed_input.day(start), typed_input.day(end)
        if ends < begins:
            raise UserError("the period ends before it starts")
        if hours < 0:
            raise UserError("hours compensated cannot be negative")
        chosen = self._label(label, answers)
        given = GIVEN_AS_TIME_OFF[time_off](hours, _written(reference))
        message = f"recorded {hours:g}h of {_label_words(chosen)}overtime {given.wording} for {begins} to {ends}"
        return self.log.write(Compensated(begins, ends, given, chosen), message, self.log.clock())

    def _label(self, typed: str, answers: Answers) -> str:
        chosen = self.labels.settle(typed, self.labels.in_use(self.log.shifts()), answers, needs_hours=True)
        if chosen:
            return chosen
        return self.log.hours.default_label


def _written(reference: str | None) -> str:
    if reference is None:
        return ""
    return reference


def _label_words(label: str) -> str:
    if label:
        return f"{label} "
    return ""
