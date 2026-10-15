from dataclasses import dataclass
from datetime import date, datetime, timedelta

from chronata.timekeeping.pc.pc_sessions import PcSession
from chronata.timekeeping.pc.start_proof import earliest_covering, start_proof
from chronata.timekeeping.record.stamps import Stamp
from chronata.timekeeping.shifts.day_entries import DayEntry
from chronata.timekeeping.shifts.shifts import Happening, Shift

LATE_ENOUGH_TO_FLAG = timedelta(minutes=15)


@dataclass(frozen=True)
class DayRecords:
    sessions: list[PcSession]
    stamps: list[Stamp]
    now: datetime


@dataclass(frozen=True)
class Line:
    what: str
    at: datetime | None
    detail: str
    mistake: int | None = None

    def time_on(self, day: date) -> str:
        if self.at is None:
            return ""
        return f"{self.at:%H:%M:%S}" if self.at.date() == day else f"{self.at:%a %d %b %H:%M}"


def day_story(entry: DayEntry, records: DayRecords) -> list[Line]:
    happened = sorted((line for piece in entry.pieces for line in _piece_lines(piece, entry, records)), key=lambda line: line.at)
    return [*_corrected(entry), *_pc_on(entry, records), *happened]


def _corrected(entry: DayEntry) -> list[Line]:
    corrections = sorted({(c.at, c.reason) for piece in entry.pieces for c in piece.corrections})
    if not corrections:
        return []
    span = f"{entry.start:%H:%M:%S} – {f'{entry.end:%H:%M:%S}' if entry.end else 'now'}"
    changed = [f"changed {at:%a %d %b %H:%M} · “{reason}”" for at, reason in corrections]
    return [Line("Corrected", None, " · ".join([span, *changed]))]


def _pc_on(entry: DayEntry, records: DayRecords) -> list[Line]:
    began = min(piece.first_start for piece in entry.counted or entry.pieces)
    session = next((s for s in records.sessions if s.covers(began)), None)
    if session is None:
        return []
    stamps = earliest_covering(records.stamps, session.first_entry)
    by = ", ".join(f"{s.authority_name} {_clock(s.time.astimezone(session.on.tzinfo), session.on)}" for s in stamps)
    return [Line("PC on", session.on, f"timestamped by {by}" if by else "not yet independently timestamped")]


def _piece_lines(piece: Shift, entry: DayEntry, records: DayRecords) -> list[Line]:
    opening, *rest = piece.happenings
    told_by_the_pc = piece.added_later and start_proof(piece, records.sessions, records.stamps).from_pc_on
    first = [] if told_by_the_pc else [_line(opening, _own_mistake_button(piece, entry))]
    return first + [_line(happening) for happening in rest]


def _own_mistake_button(piece: Shift, entry: DayEntry) -> int | None:
    if not piece.added_later or piece.voided:
        return None
    return piece.id if len(entry.counted) > 1 else None


def _line(happening: Happening, mistake: int | None = None) -> Line:
    return Line(happening.what, happening.at, happening.detail, mistake)


def _clock(moment: datetime, day: datetime) -> str:
    return f"{moment:%H:%M:%S}" if moment.date() == day.date() else f"{moment:%a %d %b %H:%M:%S}"
