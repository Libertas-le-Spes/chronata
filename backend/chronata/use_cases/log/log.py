from datetime import datetime
from functools import wraps
from typing import Callable

from chronata.timekeeping.compensation.compensation import Reconciliation, reconcile_by_label
from chronata.timekeeping.entries.new_entry import NewEntry
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.overtime import Week, combined, weeks_by_label
from chronata.timekeeping.pc.pc_sessions import PcSession, pc_sessions
from chronata.timekeeping.shifts.replay import shifts
from chronata.timekeeping.shifts.shifts import Shift
from chronata.use_cases.log.outcome import Outcome, UserError
from chronata.use_cases.log.ports import Clock, History, LabelHoursStore, RecordStore, WriteLock


def one_writer_at_a_time(operation):
    @wraps(operation)
    def locked(self, *args, **kwargs):
        with self.log.lock():
            return operation(self, *args, **kwargs)
    return locked


class Log:
    def __init__(self, record: RecordStore, history: History, label_hours: LabelHoursStore, lock: WriteLock, clock: Clock,
                 publish: Callable[["Log"], str | None] | None = None):
        self.record = record
        self.history = history
        self.label_hours = label_hours
        self.lock = lock
        self.clock = clock
        self.publish = publish

    @property
    def hours(self) -> LabelHours:
        return self.label_hours.load()

    def shifts(self) -> list[Shift]:
        return shifts(self.record.entries())

    def weeks(self) -> list[Week]:
        return combined(self.weeks_per_label(), self.hours.default_label)

    def weeks_per_label(self) -> dict[str, list[Week]]:
        return weeks_by_label(self.shifts(), self.hours, self.clock())

    def compensation(self, weeks_per_label: dict[str, list[Week]]) -> dict[str, Reconciliation]:
        return reconcile_by_label(self.record.entries(), weeks_per_label, self.hours.default_label)

    def pc_sessions(self) -> list[PcSession]:
        return pc_sessions(self.record.entries())

    def entry_count(self) -> int:
        return len(self.record.entries())

    def problems(self) -> list[str]:
        return self.record.problems()

    def shift(self, shift_id: int) -> Shift:
        found = next((shift for shift in self.shifts() if shift.id == shift_id), None)
        if found is None:
            raise UserError(f"there is no shift {shift_id}")
        return found

    def shifts_with(self, shift_ids: list[int]) -> list[Shift]:
        found = [self.shift(shift_id) for shift_id in dict.fromkeys(shift_ids)]
        if not found:
            raise UserError("choose a shift")
        return sorted(found, key=lambda shift: shift.start)

    def write(self, entry: NewEntry, message: str, now: datetime) -> Outcome:
        self.append(entry, now)
        return self.commit(message)

    def append(self, entry: NewEntry, now: datetime) -> None:
        self.record.append(entry.kind, entry.data(), now)

    def commit(self, message: str) -> Outcome:
        self.history.commit(message)
        return Outcome(message, self.published())

    def published(self) -> str | None:
        return self.publish(self) if self.publish else None

    def save_now(self) -> Outcome:
        with self.lock():
            warning = self.published()
        return Outcome("saved", warning)

