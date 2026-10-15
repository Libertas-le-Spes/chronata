from dataclasses import dataclass
from datetime import datetime

from chronata.timekeeping.pc_sessions import PcSession, session_at
from chronata.timekeeping.shifts import Shift, open_shift
from chronata.use_cases.log import Log, one_writer_at_a_time
from chronata.use_cases.outcome import Outcome
from chronata.use_cases.ports import PowerHistory


@dataclass(frozen=True)
class Interrupted:
    shift: Shift
    pc_went_off: datetime | None


class PcRecords:
    def __init__(self, log: Log, power: PowerHistory):
        self.log = log
        self.power = power

    def this_boot(self) -> PcSession | None:
        return next((s for s in self.log.pc_sessions() if s.boot == self.power.current_boot_id()), None)

    def on_since(self) -> datetime | None:
        this_boot = self.this_boot()
        return this_boot.on if this_boot else next((b.on for b in self.power.boots() if b.current), None)

    def current_boot_id(self) -> str:
        return self.power.current_boot_id()

    def interrupted(self) -> Interrupted | None:
        current = open_shift(self.log.shifts())
        this_boot = self.this_boot()
        if current is None or this_boot is None or current.since >= this_boot.on:
            return None
        went_off = self._went_off(current)
        if went_off and went_off.date() == this_boot.on.date():
            return None
        return Interrupted(current, went_off)

    @one_writer_at_a_time
    def record_sessions(self) -> Outcome | None:
        recorded = {session.boot: session for session in self.log.pc_sessions()}
        now = self.log.clock()
        written = 0
        for boot in self.power.boots():
            known = recorded.get(boot.id)
            if boot.current and known is None:
                self.log.record.append("pc_session", {"boot": boot.id, "on": boot.on.isoformat(), "off": None}, now)
                written += 1
            elif not boot.current and (known is None or known.off is None):
                data = {"boot": boot.id, "on": boot.on.isoformat(), "off": boot.last_seen.isoformat()}
                self.log.record.append("pc_session", {**data, "exact": True} if boot.off_is_exact else data, now)
                written += 1
        break_message = self._pc_off_break(now)
        if not written and not break_message:
            return None
        return self.log.commit("; ".join(part for part in (
            f"recorded PC on/off times for {written} power session{'s' if written != 1 else ''}" if written else "",
            break_message or "",
        ) if part))

    @one_writer_at_a_time
    def record_shutdown(self) -> Outcome:
        now = self.log.clock()
        on = self.on_since() or now
        data = {"boot": self.power.current_boot_id(), "on": on.isoformat(), "off": now.isoformat(), "exact": True}
        return self.log.write("pc_session", data, f"PC shutting down at {now:%Y-%m-%d %H:%M:%S}", now)

    def _went_off(self, shift: Shift) -> datetime | None:
        started_in = session_at(self.log.pc_sessions(), shift.since)
        return started_in.off if started_in else None

    def _pc_off_break(self, now: datetime) -> str | None:
        current = open_shift(self.log.shifts())
        this_boot = self.this_boot()
        if current is None or this_boot is None or current.since >= this_boot.on:
            return None
        went_off = self._went_off(current)
        if went_off is None or went_off.date() != this_boot.on.date():
            return None
        data = {"shift": current.id, "start": went_off.isoformat(), "end": this_boot.on.isoformat()}
        self.log.record.append("pc_off_break", data, now)
        return f"PC was off {went_off:%H:%M:%S}–{this_boot.on:%H:%M:%S}; not counted as work"
