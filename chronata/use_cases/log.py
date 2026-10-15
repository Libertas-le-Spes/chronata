from datetime import datetime
from functools import wraps
from typing import Callable

from chronata.timekeeping.pay import Reconciliation, reconcile
from chronata.timekeeping.pc_sessions import PcSession, pc_sessions
from chronata.timekeeping.replay import shifts
from chronata.timekeeping.shifts import Shift, completed
from chronata.timekeeping.working_day import Week, WorkingDay, weeks
from chronata.use_cases.outcome import Outcome, UserError
from chronata.use_cases.ports import Clock, History, RecordStore, WorkingDayStore, WriteLock


def one_writer_at_a_time(operation):
    @wraps(operation)
    def locked(self, *args, **kwargs):
        with self.log.lock():
            return operation(self, *args, **kwargs)
    return locked


class Log:
    def __init__(self, record: RecordStore, history: History, working_days: WorkingDayStore, lock: WriteLock, clock: Clock,
                 publish: Callable[["Log"], str | None] | None = None):
        self.record = record
        self.history = history
        self.working_days = working_days
        self.lock = lock
        self.clock = clock
        self.publish = publish

    @property
    def working_day(self) -> WorkingDay:
        return self.working_days.load()

    def shifts(self) -> list[Shift]:
        return shifts(self.record.entries())

    def weeks(self) -> list[Week]:
        return weeks(completed(self.shifts()), self.working_day)

    def reconciliation(self, selected_weeks: list[Week]) -> Reconciliation:
        return reconcile(self.record.entries(), selected_weeks)

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

    def write(self, kind: str, data: dict, message: str, now: datetime) -> Outcome:
        self.record.append(kind, data, now)
        return self.commit(message)

    def commit(self, message: str) -> Outcome:
        self.history.commit(message)
        return Outcome(message, self.published())

    def published(self) -> str | None:
        return self.publish(self) if self.publish else None

    def save_now(self) -> Outcome:
        with self.lock():
            warning = self.published()
        return Outcome("saved" if warning is None else "saved, with problems", warning)


def with_note(data: dict, note: str | None) -> dict:
    return {**data, "note": note.strip()} if note and note.strip() else data


def with_label(label: str | None) -> dict:
    return {"label": label.strip()} if label and label.strip() else {}
