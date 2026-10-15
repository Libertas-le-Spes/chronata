from datetime import datetime

from chronata.timekeeping.durations import hours
from chronata.timekeeping.shifts import open_shift, resumable, unclocked_since
from chronata.use_cases import typed_input
from chronata.use_cases.labelling import Labelling
from chronata.use_cases.log import Log, one_writer_at_a_time, with_label, with_note
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
        working_day = self.log.working_day
        chosen = working_day.default_label if label is None else self.labels.settle(label, new_label, self.labels.in_use(all_shifts))
        earlier_today = resumable(all_shifts, start)
        if earlier_today and start > earlier_today.end and (label is None or earlier_today.label == chosen):
            data = with_note({"shift": earlier_today.id, "at": start.isoformat(), "boot": self.pc.current_boot_id()}, note)
            message = f"back on today's shift at {start:%H:%M:%S} after a {hours(start - earlier_today.end)} break"
            return self.log.write("clock_resumed", data, message, now)
        if working_day.strays_from_default(chosen, start) and not off_default:
            raise OffDefaultLabel(chosen, working_day.default_label)
        data = with_note({"at": start.isoformat(), "boot": self.pc.current_boot_id(), **with_label(chosen)}, note)
        return self.log.write("clock_in", data, f"in {start:%Y-%m-%d %H:%M:%S}" + (f" on {chosen}" if chosen else ""), now)

    @one_writer_at_a_time
    def clock_out(self, at: str | None, note: str | None) -> Outcome:
        now = self.log.clock()
        current = open_shift(self.log.shifts())
        if not current:
            raise UserError("not clocked in")
        end = typed_input.moment(at, now.date(), now) if at else now
        if end <= current.since:
            raise UserError(f"{end:%H:%M:%S} is before you were last clocked in at {current.since:%H:%M:%S}")
        data = with_note({"shift": current.id, "at": end.isoformat(), "boot": self.pc.current_boot_id()}, note)
        return self.log.write("clock_out", data, f"out {end:%Y-%m-%d %H:%M:%S}, worked {hours(current.worked(end))}", now)

    def unclocked_since(self) -> datetime | None:
        return unclocked_since(self.log.shifts(), self.pc.on_since(), self.log.clock())
