from chronata.use_cases.labels.labelling import Labelling, describe_hours
from chronata.use_cases.log.log import Log, one_writer_at_a_time
from chronata.use_cases.log.outcome import Outcome, UserError
from chronata.use_cases.questions import typed_input
from chronata.use_cases.questions.questions import Answers


class WorkingDaySetup:
    def __init__(self, log: Log, labels: Labelling):
        self.log = log
        self.labels = labels

    @one_writer_at_a_time
    def configure(self, answers: Answers, default_label: str | None = None) -> Outcome:
        hours = typed_input.hours(answers)
        chosen = None if default_label is None else self.labels.settle(default_label, self.labels.in_use(self.log.shifts()), answers)
        changed = None if chosen is None else self.labels.adopt_default(chosen)
        label = self.log.hours.default_label
        self.log.label_hours.save_hours(label, hours)
        message = f"set {label or 'your'} hours: {describe_hours(hours)}, so a full day is {hours.daily_hours:g} h"
        return self.log.commit(message + (f"; {changed}" if changed else ""))

    @one_writer_at_a_time
    def set_hours(self, label: str, answers: Answers) -> Outcome:
        known = self.labels.in_use(self.log.shifts())
        chosen = self.labels.settle(label, known, Answers())
        if chosen not in known:
            raise UserError(f"there is no label '{label.strip()}'; add it first")
        hours = None if answers.no_set_hours else typed_input.hours(answers)
        self.log.label_hours.save_hours(chosen, hours)
        return self.log.commit(f"set {chosen} hours: {describe_hours(hours)}")
