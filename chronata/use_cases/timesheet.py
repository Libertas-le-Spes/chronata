from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable

from chronata.timekeeping.durations import hours
from chronata.timekeeping.labels import LabelChoice, choose, known_labels, suggested, tidy
from chronata.timekeeping.pay import Reconciliation, reconcile
from chronata.timekeeping.pc_sessions import PcSession, pc_sessions, session_at
from chronata.timekeeping.shifts import Shift, completed, open_shift, resumable, shifts, unclocked_since
from chronata.timekeeping.working_day import Week, WorkingDay, check_fits, weeks
from chronata.use_cases import typed_input
from chronata.use_cases.outcome import OffDefaultLabel, Outcome, UnconfirmedLabel, UserError
from chronata.use_cases.ports import Clock, History, PowerHistory, RecordStore, WorkingDayStore, WriteLock


@dataclass(frozen=True)
class Interrupted:
    shift: Shift
    pc_went_off: datetime | None


def _one_writer_at_a_time(operation):
    @wraps(operation)
    def locked(self, *args, **kwargs):
        with self.lock():
            return operation(self, *args, **kwargs)
    return locked


class Timesheet:
    def __init__(self, record: RecordStore, history: History, working_days: WorkingDayStore, power: PowerHistory,
                 lock: WriteLock, clock: Clock, publish: Callable[["Timesheet"], str | None] | None = None):
        self.record = record
        self.history = history
        self.working_days = working_days
        self.power = power
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

    def this_boot(self) -> PcSession | None:
        return next((s for s in self.pc_sessions() if s.boot == self.power.current_boot_id()), None)

    def pc_on_since(self) -> datetime | None:
        this_boot = self.this_boot()
        return this_boot.on if this_boot else next((b.on for b in self.power.boots() if b.current), None)

    def unclocked_since(self) -> datetime | None:
        return unclocked_since(self.shifts(), self.pc_on_since(), self.clock())

    def entry_count(self) -> int:
        return len(self.record.entries())

    def problems(self) -> list[str]:
        return self.record.problems()

    def interrupted(self) -> Interrupted | None:
        current = open_shift(self.shifts())
        this_boot = self.this_boot()
        if current is None or this_boot is None or current.since >= this_boot.on:
            return None
        went_off = self._went_off(current)
        if went_off and went_off.date() == this_boot.on.date():
            return None
        return Interrupted(current, went_off)

    @_one_writer_at_a_time
    def record_pc_sessions(self) -> Outcome | None:
        recorded = {session.boot: session for session in self.pc_sessions()}
        now = self.clock()
        written = 0
        for boot in self.power.boots():
            known = recorded.get(boot.id)
            if boot.current and known is None:
                self.record.append("pc_session", {"boot": boot.id, "on": boot.on.isoformat(), "off": None}, now)
                written += 1
            elif not boot.current and (known is None or known.off is None):
                data = {"boot": boot.id, "on": boot.on.isoformat(), "off": boot.last_seen.isoformat()}
                self.record.append("pc_session", {**data, "exact": True} if boot.off_is_exact else data, now)
                written += 1
        break_message = self._pc_off_break(now)
        if not written and not break_message:
            return None
        message = "; ".join(part for part in (
            f"recorded PC on/off times for {written} power session{'s' if written != 1 else ''}" if written else "",
            break_message or "",
        ) if part)
        self.history.commit(message)
        return Outcome(message, self._publish())

    @_one_writer_at_a_time
    def explain_break(self, shift_id: int, start: str, reason: str) -> Outcome:
        shift = self._shift(shift_id)
        gap = next((b for b in shift.breaks if b.start.isoformat() == start), None)
        if gap is None:
            raise UserError(f"shift {shift_id} has no break starting at {start}")
        message = f"noted why the PC was off from {gap.start:%H:%M}: {typed_input.required(reason)}"
        return self._write("break_explained", {"shift": shift.id, "start": start, "reason": reason.strip()}, message, self.clock())

    @_one_writer_at_a_time
    def configure(self, lunch_answer: str, shift_answer: str, default_label: str | None = None, new_label: bool = False) -> Outcome:
        lunch_start, lunch_minutes = typed_input.lunch(lunch_answer)
        shift_start, shift_end = typed_input.shift(shift_answer)
        try:
            check_fits(shift_start, shift_end, lunch_start, lunch_minutes)
        except ValueError as error:
            raise UserError(str(error))
        chosen = None if default_label is None else self._settled_label(default_label, new_label, self._labels_in_use(self.shifts()))
        self.working_days.save(shift_start, shift_end, lunch_start, lunch_minutes)
        message = (
            f"set shift {shift_start:%H:%M}–{shift_end:%H:%M} with lunch at {lunch_start:%H:%M} for {lunch_minutes} min, "
            f"so a full day is {hours(timedelta(hours=self.working_day.daily_hours))}"
        )
        if chosen is not None and chosen != self.working_day.default_label:
            self.working_days.save_default_label(chosen)
            message += f"; {_default_described(chosen)}"
        self.history.commit(message)
        return Outcome(message, self._publish())

    @_one_writer_at_a_time
    def set_default_label(self, label: str, new_label: bool = False) -> Outcome:
        chosen = self._settled_label(label, new_label, self._labels_in_use(self.shifts()))
        if chosen == self.working_day.default_label:
            raise UserError(f"{chosen} is already the default" if chosen else "there is no default label to clear")
        self.working_days.save_default_label(chosen)
        message = _default_described(chosen)
        self.history.commit(message)
        return Outcome(message, self._publish())

    @_one_writer_at_a_time
    def record_shutdown(self) -> Outcome:
        now = self.clock()
        on = self.pc_on_since() or now
        data = {"boot": self.power.current_boot_id(), "on": on.isoformat(), "off": now.isoformat(), "exact": True}
        return self._write("pc_session", data, f"PC shutting down at {now:%Y-%m-%d %H:%M:%S}", now)

    @_one_writer_at_a_time
    def clock_in(self, at: str | None, note: str | None, label: str | None = None, new_label: bool = False, off_default: bool = False) -> Outcome:
        now = self.clock()
        all_shifts = self.shifts()
        current = open_shift(all_shifts)
        if current:
            raise UserError(f"already clocked in since {current.start:%Y-%m-%d %H:%M:%S}")
        start = typed_input.moment(at, now.date(), now) if at else now
        working_day = self.working_day
        chosen = working_day.default_label if label is None else self._settled_label(label, new_label, self._labels_in_use(all_shifts))
        earlier_today = resumable(all_shifts, start)
        if earlier_today and start > earlier_today.end and (label is None or earlier_today.label == chosen):
            data = _with_note({"shift": earlier_today.id, "at": start.isoformat(), "boot": self.power.current_boot_id()}, note)
            message = f"back on today's shift at {start:%H:%M:%S} after a {hours(start - earlier_today.end)} break"
            return self._write("clock_resumed", data, message, now)
        if working_day.strays_from_default(chosen, start) and not off_default:
            raise OffDefaultLabel(chosen, working_day.default_label)
        data = _with_note({"at": start.isoformat(), "boot": self.power.current_boot_id(), **_with_label(chosen)}, note)
        return self._write("clock_in", data, f"in {start:%Y-%m-%d %H:%M:%S}" + (f" on {chosen}" if chosen else ""), now)

    @_one_writer_at_a_time
    def clock_out(self, at: str | None, note: str | None) -> Outcome:
        now = self.clock()
        current = open_shift(self.shifts())
        if not current:
            raise UserError("not clocked in")
        end = typed_input.moment(at, now.date(), now) if at else now
        if end <= current.since:
            raise UserError(f"{end:%H:%M:%S} is before you were last clocked in at {current.since:%H:%M:%S}")
        data = _with_note({"shift": current.id, "at": end.isoformat(), "boot": self.power.current_boot_id()}, note)
        return self._write("clock_out", data, f"out {end:%Y-%m-%d %H:%M:%S}, worked {hours(current.worked(end))}", now)

    @_one_writer_at_a_time
    def label(self, shift_id: int, label: str, new_label: bool = False) -> Outcome:
        shift = self._shift(shift_id)
        label = self._settled_label(label, new_label, self._labels_in_use(self.shifts()))
        if shift.label == label:
            raise UserError(f"shift {shift_id} is already labelled {label or 'with nothing'}")
        return self._write("shift_labelled", {"shift": shift.id, "label": label}, f"labelled shift {shift.id} {label or '(no label)'}", self.clock())

    def suggested_label(self) -> str:
        return suggested(self.shifts(), self.clock(), self.working_day.default_label)

    def check_label(self, typed: str) -> LabelChoice:
        return choose(typed, self._labels_in_use(self.shifts()))

    @_one_writer_at_a_time
    def rename_label(self, old: str, new: str, new_label: bool = False) -> Outcome:
        all_shifts = self.shifts()
        known = known_labels(all_shifts)
        current = choose(old, known)
        if not current.label or not current.exists:
            raise UserError(f"there is no label '{old.strip()}'")
        others = [shift for shift in all_shifts if shift.label != current.label]
        target = self._settled_label(new, new_label, known_labels(others)) if _key_differs(new, current.label) else tidy(new)
        if not target:
            raise UserError("give the new name for the label")
        if target == current.label:
            raise UserError(f"the label is already called {target}")
        affected = [shift for shift in all_shifts if shift.label == current.label]
        now = self.clock()
        for shift in affected:
            self.record.append("shift_labelled", {"shift": shift.id, "label": target, "reason": f"label renamed from {current.label}"}, now)
        merged = target in known
        message = (f"merged {current.label} into {target}" if merged else f"renamed label {current.label} to {target}") + f" on {len(affected)} shift{'s' if len(affected) != 1 else ''}"
        if self.working_day.default_label == current.label:
            self.working_days.save_default_label(target)
            message += f"; {target} is now the default"
        self.history.commit(message)
        return Outcome(message, self._publish())

    @_one_writer_at_a_time
    def add(self, day: str, start: str, end: str, reason: str, note: str | None, label: str = "", new_label: bool = False) -> Outcome:
        now = self.clock()
        begins = typed_input.moment(start, typed_input.day(day), now)
        ends = typed_input.end_after(begins, end, now)
        if ends > now:
            raise UserError("that shift has not ended yet; clock in instead")
        label = self._settled_label(label, new_label, self._labels_in_use(self.shifts()))
        data = _with_note({"start": begins.isoformat(), "end": ends.isoformat(), "reason": typed_input.required(reason), **_with_label(label)}, note)
        return self._write("shift_added", data, f"added {begins:%Y-%m-%d %H:%M:%S} to {ends:%H:%M:%S}, worked {hours(ends - begins)}", now)

    @_one_writer_at_a_time
    def correct(self, shift_id: int, start: str | None, end: str | None, reason: str) -> Outcome:
        now = self.clock()
        shift = self._shift(shift_id)
        if shift.end is None:
            raise UserError("clock out of this shift before correcting it")
        begins = typed_input.moment(start, shift.start.date(), now) if start else shift.start
        ends = typed_input.end_after(begins, end, now) if end else shift.end
        if ends <= begins or ends > now:
            raise UserError("a shift has to end after it starts, and not in the future")
        data = {"shift": shift.id, "start": begins.isoformat(), "end": ends.isoformat(), "reason": typed_input.required(reason)}
        return self._write("shift_corrected", data, f"corrected shift {shift.id} to {begins:%Y-%m-%d %H:%M:%S} to {ends:%H:%M:%S}", now)

    @_one_writer_at_a_time
    def strike(self, shift_id: int, reason: str) -> Outcome:
        shift = self._shift(shift_id)
        if shift.voided:
            raise UserError(f"shift {shift_id} is already struck out")
        return self._write("shift_voided", {"shift": shift.id, "reason": typed_input.required(reason)}, f"struck out shift {shift.id}", self.clock())

    @_one_writer_at_a_time
    def record_payment(self, start: str, end: str, paid_hours: float, time_off: bool, reference: str | None) -> Outcome:
        begins, ends = typed_input.day(start), typed_input.day(end)
        if ends < begins:
            raise UserError("the pay period ends before it starts")
        if paid_hours < 0:
            raise UserError("hours paid cannot be negative")
        data = {"from": begins.isoformat(), "to": ends.isoformat(), "hours": paid_hours,
                "kind": "time_off" if time_off else "paid", "reference": reference or ""}
        message = f"recorded {paid_hours:g}h of overtime {'given as time off' if time_off else 'paid'} for {begins} to {ends}"
        return self._write("compensation", data, message, self.clock())

    @_one_writer_at_a_time
    def save_now(self) -> Outcome:
        warning = self._publish()
        return Outcome("saved" if warning is None else "saved, with problems", warning)

    def _went_off(self, shift: Shift) -> datetime | None:
        started_in = session_at(self.pc_sessions(), shift.since)
        return started_in.off if started_in else None

    def _pc_off_break(self, now: datetime) -> str | None:
        current = open_shift(self.shifts())
        this_boot = self.this_boot()
        if current is None or this_boot is None or current.since >= this_boot.on:
            return None
        went_off = self._went_off(current)
        if went_off is None or went_off.date() != this_boot.on.date():
            return None
        data = {"shift": current.id, "start": went_off.isoformat(), "end": this_boot.on.isoformat()}
        self.record.append("pc_off_break", data, now)
        return f"PC was off {went_off:%H:%M:%S}–{this_boot.on:%H:%M:%S}; not counted as work"

    def _labels_in_use(self, all_shifts: list[Shift]) -> list[str]:
        known = known_labels(all_shifts)
        default = self.working_day.default_label
        return known + [default] if default and default not in known else known

    def _settled_label(self, typed: str | None, confirmed_new: bool, known: list[str]) -> str:
        choice = choose(typed or "", known)
        if not choice.exists and choice.near_misses and not confirmed_new:
            raise UnconfirmedLabel(choice.label, choice.near_misses)
        return choice.label

    def _publish(self) -> str | None:
        return self.publish(self) if self.publish else None

    def _shift(self, shift_id: int) -> Shift:
        found = next((shift for shift in self.shifts() if shift.id == shift_id), None)
        if found is None:
            raise UserError(f"there is no shift {shift_id}")
        return found

    def _write(self, kind: str, data: dict, message: str, now: datetime) -> Outcome:
        self.record.append(kind, data, now)
        self.history.commit(message)
        return Outcome(message, self._publish())


def _with_note(data: dict, note: str | None) -> dict:
    return {**data, "note": note.strip()} if note and note.strip() else data


def _default_described(label: str) -> str:
    return f"made {label} the default label" if label else "cleared the default label"


def _key_differs(typed: str, label: str) -> bool:
    return tidy(typed).casefold() != label.casefold()


def _with_label(label: str | None) -> dict:
    return {"label": label.strip()} if label and label.strip() else {}
