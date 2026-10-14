from dataclasses import dataclass
from datetime import datetime, timedelta

from chronata.timekeeping.record import Entry

NONE = timedelta()


@dataclass(frozen=True)
class Boot:
    id: str
    on: datetime
    last_seen: datetime
    current: bool


@dataclass(frozen=True)
class PcSession:
    boot: str
    on: datetime
    off: datetime | None
    exact: bool = False


@dataclass(frozen=True)
class Support:
    covered: timedelta
    length: timedelta
    sessions: tuple[PcSession, ...]
    before_records: bool

    @property
    def share(self) -> float:
        return self.covered / self.length if self.length > NONE else 0.0


def pc_sessions(entries: list[Entry]) -> list[PcSession]:
    latest: dict[str, PcSession] = {}
    for entry in entries:
        if entry.kind == "pc_session":
            data = entry.data
            off = datetime.fromisoformat(data["off"]) if data.get("off") else None
            latest[data["boot"]] = PcSession(data["boot"], datetime.fromisoformat(data["on"]), off, bool(data.get("exact")))
    return sorted(latest.values(), key=lambda session: session.on)


def session_at(sessions: list[PcSession], moment: datetime) -> PcSession | None:
    return next((s for s in sessions if s.on <= moment and (s.off is None or moment <= s.off)), None)


def support(start: datetime, end: datetime | None, sessions: list[PcSession], now: datetime) -> Support:
    finish = end or now
    overlapping = tuple(s for s in sessions if s.on < finish and (s.off or now) > start)
    covered = sum((min(finish, s.off or now) - max(start, s.on) for s in overlapping), NONE)
    before_records = not sessions or start < sessions[0].on
    return Support(covered, finish - start, overlapping, before_records)
