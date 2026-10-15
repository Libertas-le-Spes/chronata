from datetime import timedelta

from chronata.timekeeping.durations import hours
from chronata.timekeeping.working_day import check_fits
from chronata.use_cases import typed_input
from chronata.use_cases.labelling import Labelling
from chronata.use_cases.log import Log, one_writer_at_a_time
from chronata.use_cases.outcome import Outcome, UserError


class WorkingDaySetup:
    def __init__(self, log: Log, labels: Labelling):
        self.log = log
        self.labels = labels

    @one_writer_at_a_time
    def configure(self, lunch_answer: str, shift_answer: str, default_label: str | None = None, new_label: bool = False) -> Outcome:
        lunch_start, lunch_minutes = typed_input.lunch(lunch_answer)
        shift_start, shift_end = typed_input.shift(shift_answer)
        try:
            check_fits(shift_start, shift_end, lunch_start, lunch_minutes)
        except ValueError as error:
            raise UserError(str(error))
        chosen = None if default_label is None else self.labels.settle(default_label, new_label, self.labels.in_use(self.log.shifts()))
        self.log.working_days.save(shift_start, shift_end, lunch_start, lunch_minutes)
        message = (
            f"set shift {shift_start:%H:%M}–{shift_end:%H:%M} with lunch at {lunch_start:%H:%M} for {lunch_minutes} min, "
            f"so a full day is {hours(timedelta(hours=self.log.working_day.daily_hours))}"
        )
        changed = None if chosen is None else self.labels.adopt_default(chosen)
        return self.log.commit(message + (f"; {changed}" if changed else ""))
