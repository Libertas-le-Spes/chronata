import fcntl
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from functools import wraps
from pathlib import Path
from typing import Callable

from chronata import journal, setup, verification
from chronata.audit_trail import AuditTrail
from chronata.compensation import Reconciliation, reconcile
from chronata.journal import Boot
from chronata.ledger import Ledger
from chronata.pc_sessions import PcSession, pc_sessions, session_at
from chronata.report import hours
from chronata.rules import Rules, Week, weeks
from chronata.settings import load_rules, save_rules
from chronata.shifts import Break, Shift, completed, open_shift, resumable, shifts

LEDGER_FILE = "ledger.jsonl"


class UserError(Exception):
    pass


@dataclass(frozen=True)
class Outcome:
    message: str
    warning: str | None


@dataclass(frozen=True)
class Interrupted:
    shift: Shift
    pc_went_off: datetime | None


def _local_now() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


def _one_writer_at_a_time(operation):
    @wraps(operation)
    def locked(self, *args, **kwargs):
        with open(self.directory / ".git" / "chronata.lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return operation(self, *args, **kwargs)
    return locked


class Timesheet:
    def __init__(
        self,
        directory: Path,
        clock: Callable[[], datetime] = _local_now,
        boots: Callable[[], list[Boot]] = journal.boots,
        boot_id: Callable[[], str] = journal.current_boot_id,
        publish: Callable[["Timesheet"], str | None] | None = None,
    ):
        directory.mkdir(parents=True, exist_ok=True)
        self.directory = directory
        self.ledger = Ledger(directory / LEDGER_FILE)
        self.trail = AuditTrail(directory)
        self.trail.ensure()
        self.clock = clock
        self.boots = boots
        self.boot_id = boot_id
        self.publish = publish

    @property
    def rules(self) -> Rules:
        return load_rules(self.directory)

    def shifts(self) -> list[Shift]:
        return shifts(self.ledger.entries())

    def weeks(self) -> list[Week]:
        return weeks(completed(self.shifts()), self.rules)

    def reconciliation(self, selected_weeks: list[Week]) -> Reconciliation:
        return reconcile(self.ledger.entries(), selected_weeks)

    def pc_sessions(self) -> list[PcSession]:
        return pc_sessions(self.ledger.entries())

    def interrupted(self) -> Interrupted | None:
        current = open_shift(self.shifts())
        sessions = self.pc_sessions()
        this_boot = next((s for s in sessions if s.boot == self.boot_id()), None)
        if current is None or this_boot is None or current.since >= this_boot.on:
            return None
        started_in = session_at(sessions, current.since)
        return Interrupted(current, started_in.off if started_in else None)

    @_one_writer_at_a_time
    def record_pc_sessions(self) -> Outcome | None:
        recorded = {session.boot: session for session in self.pc_sessions()}
        missing = []
        for boot in self.boots():
            known = recorded.get(boot.id)
            if boot.current and known is None:
                missing.append({"boot": boot.id, "on": boot.on.isoformat(), "off": None})
            elif not boot.current and (known is None or known.off is None):
                missing.append({"boot": boot.id, "on": boot.on.isoformat(), "off": boot.last_seen.isoformat()})
        if not missing:
            return None
        now = self.clock()
        for data in missing:
            self.ledger.append("pc_session", data, now)
        message = f"recorded PC on/off times for {len(missing)} power session{'s' if len(missing) > 1 else ''}"
        self.trail.commit(message)
        return Outcome(message, self._publish())

    @_one_writer_at_a_time
    def configure(self, lunch_answer: str, shift_answer: str) -> Outcome:
        try:
            lunch_start, lunch_minutes = setup.lunch(lunch_answer)
            shift_start, shift_end = setup.shift(shift_answer)
            setup.check_fit(shift_start, shift_end, lunch_start, lunch_minutes)
        except ValueError as error:
            raise UserError(str(error))
        save_rules(self.directory, shift_start, shift_end, lunch_start, lunch_minutes)
        rules = self.rules
        message = (
            f"set shift {shift_start:%H:%M}–{shift_end:%H:%M} with lunch at {lunch_start:%H:%M} for {lunch_minutes} min, "
            f"so a normal day is {hours(timedelta(hours=rules.daily_hours))}"
        )
        self.trail.commit(message)
        return Outcome(message, self._publish())

    @_one_writer_at_a_time
    def record_shutdown(self) -> Outcome | None:
        now = self.clock()
        this_boot = next((s for s in self.pc_sessions() if s.boot == self.boot_id()), None)
        on = this_boot.on if this_boot else next((b.on for b in self.boots() if b.current), now)
        self.ledger.append("pc_session", {"boot": self.boot_id(), "on": on.isoformat(), "off": now.isoformat(), "exact": True}, now)
        message = f"PC shutting down at {now:%Y-%m-%d %H:%M:%S}"
        self.trail.commit(message)
        return Outcome(message, self._publish())

    def problems(self, include_history: bool) -> list[str]:
        if not include_history:
            return self.ledger.verify()
        return verification.check(self.ledger, self.directory).problems + self.trail.rewrites(LEDGER_FILE)

    @_one_writer_at_a_time
    def clock_in(self, at: str | None, note: str | None, label: str = "") -> Outcome:
        now = self.clock()
        all_shifts = self.shifts()
        current = open_shift(all_shifts)
        if current:
            raise UserError(f"already clocked in since {current.start:%Y-%m-%d %H:%M:%S}")
        start = _moment(at, now.date(), now) if at else now
        earlier_today = resumable(all_shifts, start)
        if earlier_today and start > earlier_today.end:
            gap = Break(earlier_today.end, start)
            data = _with_note({"shift": earlier_today.id, "at": start.isoformat(), "boot": self.boot_id()}, note)
            return self._write("clock_resumed", data, f"back on today's shift at {start:%H:%M:%S} after a {hours(gap.end - gap.start)} break", now)
        data = _with_note({"at": start.isoformat(), "boot": self.boot_id(), **_with_label(label)}, note)
        return self._write("clock_in", data, f"in {start:%Y-%m-%d %H:%M:%S}" + (f" on {label.strip()}" if label.strip() else ""), now)

    @_one_writer_at_a_time
    def label(self, shift_id: int, label: str) -> Outcome:
        shift = self._shift(shift_id)
        if shift.label == label.strip():
            raise UserError(f"shift {shift_id} is already labelled {label.strip() or 'with nothing'}")
        return self._write("shift_labelled", {"shift": shift.id, "label": label.strip()},
                           f"labelled shift {shift.id} {label.strip() or '(no label)'}", self.clock())

    @_one_writer_at_a_time
    def clock_out(self, at: str | None, note: str | None) -> Outcome:
        now = self.clock()
        current = open_shift(self.shifts())
        if not current:
            raise UserError("not clocked in")
        end = _moment(at, now.date(), now) if at else now
        if end <= current.start:
            raise UserError(f"{end:%H:%M:%S} is before you clocked in at {current.start:%H:%M:%S}")
        return self._write(
            "clock_out",
            _with_note({"shift": current.id, "at": end.isoformat(), "boot": self.boot_id()}, note),
            f"out {end:%Y-%m-%d %H:%M:%S}, worked {hours(self.rules.worked(current.segments(end)))}",
            now,
        )

    @_one_writer_at_a_time
    def add(self, day: str, start: str, end: str, reason: str, note: str | None, label: str = "") -> Outcome:
        now = self.clock()
        begins = _moment(start, _day(day), now)
        ends = _end(begins, end, now)
        if ends > now:
            raise UserError("that shift has not ended yet; clock in instead")
        return self._write(
            "shift_added",
            _with_note({"start": begins.isoformat(), "end": ends.isoformat(), "reason": _required(reason), **_with_label(label)}, note),
            f"added {begins:%Y-%m-%d %H:%M:%S} to {ends:%H:%M:%S}, worked {hours(self.rules.worked([(begins, ends)]))}",
            now,
        )

    @_one_writer_at_a_time
    def correct(self, shift_id: int, start: str | None, end: str | None, reason: str) -> Outcome:
        now = self.clock()
        shift = self._shift(shift_id)
        if shift.end is None:
            raise UserError("clock out of this shift before correcting it")
        begins = _moment(start, shift.start.date(), now) if start else shift.start
        ends = _end(begins, end, now) if end else shift.end
        if ends <= begins or ends > now:
            raise UserError("a shift has to end after it starts, and not in the future")
        return self._write(
            "shift_corrected",
            {"shift": shift.id, "start": begins.isoformat(), "end": ends.isoformat(), "reason": _required(reason)},
            f"corrected shift {shift.id} to {begins:%Y-%m-%d %H:%M:%S} to {ends:%H:%M:%S}",
            now,
        )

    @_one_writer_at_a_time
    def strike(self, shift_id: int, reason: str) -> Outcome:
        shift = self._shift(shift_id)
        if shift.voided:
            raise UserError(f"shift {shift_id} is already struck out")
        return self._write("shift_voided", {"shift": shift.id, "reason": _required(reason)}, f"struck out shift {shift.id}", self.clock())

    @_one_writer_at_a_time
    def record_payment(self, start: str, end: str, paid_hours: float, time_off: bool, reference: str | None) -> Outcome:
        begins, ends = _day(start), _day(end)
        if ends < begins:
            raise UserError("the pay period ends before it starts")
        if paid_hours < 0:
            raise UserError("hours paid cannot be negative")
        return self._write(
            "compensation",
            {"from": begins.isoformat(), "to": ends.isoformat(), "hours": paid_hours,
             "kind": "time_off" if time_off else "paid", "reference": reference or ""},
            f"recorded {paid_hours:g}h of overtime {'given as time off' if time_off else 'paid'} for {begins} to {ends}",
            self.clock(),
        )

    @_one_writer_at_a_time
    def save_now(self) -> Outcome:
        warning = self._publish()
        return Outcome("saved" if warning is None else "saved, with problems", warning)

    def _publish(self) -> str | None:
        return self.publish(self) if self.publish else None

    def _shift(self, shift_id: int) -> Shift:
        found = next((shift for shift in self.shifts() if shift.id == shift_id), None)
        if found is None:
            raise UserError(f"there is no shift {shift_id}")
        return found

    def _write(self, kind: str, data: dict, message: str, now: datetime) -> Outcome:
        self.ledger.append(kind, data, now)
        self.trail.commit(message)
        return Outcome(message, self._publish())


def _with_note(data: dict, note: str | None) -> dict:
    return {**data, "note": note.strip()} if note and note.strip() else data


def _with_label(label: str | None) -> dict:
    return {"label": label.strip()} if label and label.strip() else {}


def _required(reason: str | None) -> str:
    if not reason or not reason.strip():
        raise UserError("a reason is required, so the record explains itself")
    return reason.strip()


def _day(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        raise UserError(f"'{text}' is not a date like 2026-10-14")


def _moment(text: str, day: date, now: datetime, allow_future: bool = False) -> datetime:
    try:
        moment = datetime.fromisoformat(text) if " " in text or "T" in text else datetime.combine(day, time.fromisoformat(text))
    except (TypeError, ValueError):
        raise UserError(f"'{text}' is not a time like 08:04, 08:04:31 or 2026-10-14 08:04")
    moment = moment.astimezone()
    if moment > now and not allow_future:
        raise UserError(f"{moment:%Y-%m-%d %H:%M:%S} is in the future")
    return moment


def _end(start: datetime, text: str, now: datetime) -> datetime:
    end = _moment(text, start.date(), now, allow_future=True)
    time_only = " " not in text and "T" not in text
    return end + timedelta(days=1) if time_only and end <= start else end
