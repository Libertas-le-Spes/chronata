from datetime import datetime

from chronata.timekeeping.durations import hours
from chronata.timekeeping.entries.clocking import ClockIn, ClockOut, ClockResumed
from chronata.timekeeping.shifts import Shift, open_shift
from chronata.timekeeping.today import resumable, unclocked_since
from chronata.use_cases import typed_input
from chronata.use_cases.labelling import Labelling
from chronata.use_cases.log import Log, one_writer_at_a_time
from chronata.use_cases.outcome import Outcome, UserError
from chronata.use_cases.questions import Answers, OffDefaultLabel
from chronata.use_cases.pc_records import PcRecords


class Clocking:
    def __init__(self, log: Log, pc: PcRecords, labels: Labelling):
        self.log = log
        self.pc = pc
        self.labels = labels

    @one_writer_at_a_time
    def clock_in(self, at: str | None, note: str | None, label: str | None = None, answers: Answers = Answers()) -> Outcome:
        now = self.log.clock()
        all_shifts = self.log.shifts()
        _refuse_if_clocked_in(all_shifts)
        start = typed_input.moment(at, now.date(), now) if at else now
        chosen = self._chosen_label(label, all_shifts, answers)
        carried_on = _carried_on(all_shifts, start, chosen, label is None)
        if carried_on:
            message = f"back on today's shift at {start:%H:%M:%S} after a {hours(start - carried_on.end)} break"
            return self.log.write(ClockResumed(carried_on.id, start, self.pc.current_boot_id(), note), message, now)
        self._confirm_off_default(chosen, start, answers)
        message = f"in {start:%Y-%m-%d %H:%M:%S}" + (f" on {chosen}" if chosen else "")
        return self.log.write(ClockIn(start, self.pc.current_boot_id(), chosen, note), message, now)

    def _chosen_label(self, label: str | None, all_shifts: list[Shift], answers: Answers) -> str:
        if label is None:
            return self.log.hours.default_label
        return self.labels.settle(label, self.labels.in_use(all_shifts), answers, needs_hours=True)

    def _confirm_off_default(self, chosen: str, start: datetime, answers: Answers) -> None:
        label_hours = self.log.hours
        if label_hours.strays_from_default(chosen, start) and not answers.off_default:
            raise OffDefaultLabel(chosen, label_hours.default_label)

    @one_writer_at_a_time
    def clock_out(self, at: str | None, note: str | None) -> Outcome:
        now = self.log.clock()
        current = open_shift(self.log.shifts())
        if not current:
            raise UserError("not clocked in")
        end = typed_input.moment(at, now.date(), now) if at else now
        if end <= current.since:
            raise UserError(f"{end:%H:%M:%S} is before you were last clocked in at {current.since:%H:%M:%S}")
        message = f"out {end:%Y-%m-%d %H:%M:%S}, worked {hours(current.worked(end))}"
        return self.log.write(ClockOut(current.id, end, self.pc.current_boot_id(), note), message, now)

    def unclocked_since(self) -> datetime | None:
        return unclocked_since(self.log.shifts(), self.pc.on_since(), self.log.clock())


def _refuse_if_clocked_in(all_shifts: list[Shift]) -> None:
    current = open_shift(all_shifts)
    if current:
        raise UserError(f"already clocked in since {current.start:%Y-%m-%d %H:%M:%S}")


def _carried_on(all_shifts: list[Shift], start: datetime, chosen: str, label_left_out: bool) -> Shift | None:
    earlier_today = resumable(all_shifts, start)
    if earlier_today is None or start <= earlier_today.end:
        return None
    return earlier_today if label_left_out or earlier_today.label == chosen else None
