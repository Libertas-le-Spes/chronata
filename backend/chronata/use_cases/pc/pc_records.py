from dataclasses import dataclass
from datetime import datetime

from chronata.timekeeping.entries.pc import PcOffBreak, PowerSession
from chronata.timekeeping.pc.pc_sessions import Boot, PcSession, session_at
from chronata.timekeeping.shifts.shifts import Shift, open_shift
from chronata.use_cases.log.log import Log, one_writer_at_a_time
from chronata.use_cases.log.outcome import Outcome
from chronata.use_cases.log.ports import PowerHistory


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
        carried_over = self._open_from_before_this_boot()
        if carried_over is None:
            return None
        current, this_boot = carried_over
        went_off = self._went_off(current)
        return None if _same_day(went_off, this_boot.on) else Interrupted(current, went_off)

    @one_writer_at_a_time
    def record_sessions(self) -> Outcome | None:
        recorded = {session.boot: session for session in self.log.pc_sessions()}
        now = self.log.clock()
        sessions = [session for boot in self.power.boots() if (session := _still_to_record(boot, recorded.get(boot.id)))]
        for session in sessions:
            self.log.append(session, now)
        written = [f"recorded PC on/off times for {len(sessions)} power session{'s' if len(sessions) != 1 else ''}"] if sessions else []
        parts = written + [part for part in [self._pc_off_break(now)] if part]
        return self.log.commit("; ".join(parts)) if parts else None

    @one_writer_at_a_time
    def record_shutdown(self) -> Outcome:
        now = self.log.clock()
        on = self.on_since() or now
        return self.log.write(PowerSession(self.power.current_boot_id(), on, now, True), f"PC shutting down at {now:%Y-%m-%d %H:%M:%S}", now)

    def _went_off(self, shift: Shift) -> datetime | None:
        started_in = session_at(self.log.pc_sessions(), shift.since)
        return started_in.off if started_in else None

    def _open_from_before_this_boot(self) -> tuple[Shift, PcSession] | None:
        current = open_shift(self.log.shifts())
        this_boot = self.this_boot()
        if current is None or this_boot is None:
            return None
        return (current, this_boot) if current.since < this_boot.on else None

    def _pc_off_break(self, now: datetime) -> str | None:
        carried_over = self._open_from_before_this_boot()
        if carried_over is None:
            return None
        current, this_boot = carried_over
        went_off = self._went_off(current)
        if not _same_day(went_off, this_boot.on):
            return None
        self.log.append(PcOffBreak(current.id, went_off, this_boot.on), now)
        return f"PC was off {went_off:%H:%M:%S}–{this_boot.on:%H:%M:%S}; not counted as work"


def _same_day(went_off: datetime | None, came_on: datetime) -> bool:
    return went_off is not None and went_off.date() == came_on.date()


def _still_to_record(boot: Boot, known: PcSession | None) -> PowerSession | None:
    if boot.current:
        return PowerSession(boot.id, boot.on, None) if known is None else None
    if known is not None and known.off is not None:
        return None
    return PowerSession(boot.id, boot.on, boot.last_seen, boot.off_is_exact)
