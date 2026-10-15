from datetime import datetime

from chronata.timekeeping.durations import hours
from chronata.timekeeping.entries.clocking import ClockIn, ClockOut, ClockResumed
from chronata.timekeeping.shifts import open_shift
from chronata.timekeeping.today import resumable, unclocked_since
from chronata.use_cases import typed_input
from chronata.use_cases.labelling import Labelling
from chronata.use_cases.log import Log, one_writer_at_a_time
from chronata.use_cases.outcome import OffDefaultLabel, Outcome, UserError
from chronata.use_cases.pc_records import PcRecords


class Clocking:
    def __init__(self, log: Log, pc: PcRecords, labels: Labelling):
        self.log = log
        self.pc = pc
        self.labels = labels

    @one_writer_at_a_time
    def clock_in(self, at: str | None, note: str | None, label: str | None = None, new_label: bool = False, off_default: bool = False) -> Outcome:
        now = self.log.clock()
        all_shifts = self.log.shifts()
        current = open_shift(all_shifts)
        if current:
            raise UserError(f"already clocked in since {current.start:%Y-%m-%d %H:%M:%S}")
        start = typed_input.moment(at, now.date(), now) if at else now
        label_hours = self.log.hours
        chosen = label_hours.default_label if label is None else self.labels.settle(label, new_label, self.labels.in_use(all_shifts), needs_hours=True)
        earlier_today = resumable(all_shifts, start)
        if earlier_today and start > earlier_today.end and (label is None or earlier_today.label == chosen):
            message = f"back on today's shift at {start:%H:%M:%S} after a {hours(start - earlier_today.end)} break"
            return self.log.write(ClockResumed(earlier_today.id, start, self.pc.current_boot_id(), note), message, now)
        if label_hours.strays_from_default(chosen, start) and not off_default:
            raise OffDefaultLabel(chosen, label_hours.default_label)
        message = f"in {start:%Y-%m-%d %H:%M:%S}" + (f" on {chosen}" if chosen else "")
        return self.log.write(ClockIn(start, self.pc.current_boot_id(), chosen, note), message, now)

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
