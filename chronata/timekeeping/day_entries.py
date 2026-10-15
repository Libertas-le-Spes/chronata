from dataclasses import dataclass
from datetime import date, datetime, timedelta

from chronata.timekeeping.pc_sessions import PcSession, support
from chronata.timekeeping.shifts import Shift


@dataclass(frozen=True)
class DayEntry:
    day: date
    label: str
    pieces: tuple[Shift, ...]

    @property
    def counted(self) -> tuple[Shift, ...]:
        return tuple(piece for piece in self.pieces if not piece.voided)

    @property
    def voided(self) -> bool:
        return not self.counted

    @property
    def start(self) -> datetime:
        return min(piece.start for piece in self.counted or self.pieces)

    @property
    def end(self) -> datetime | None:
        shown = self.counted or self.pieces
        if any(piece.end is None for piece in shown):
            return None
        return max(piece.end for piece in shown)

    def worked(self, now: datetime) -> timedelta:
        return sum((piece.worked(piece.end or now) for piece in self.counted), timedelta())


def day_entries(all_shifts: list[Shift]) -> list[DayEntry]:
    grouped: dict[tuple[date, str], list[Shift]] = {}
    for shift in sorted(all_shifts, key=lambda s: s.start):
        grouped.setdefault((shift.start.date(), shift.label), []).append(shift)
    entries = [DayEntry(day, label, tuple(pieces)) for (day, label), pieces in grouped.items()]
    return sorted(entries, key=lambda entry: entry.start)


def pc_share(entry: DayEntry, sessions: list[PcSession], now: datetime) -> float | None:
    backings = [support(piece.start, piece.end, sessions, now) for piece in entry.counted]
    length = sum((backing.length for backing in backings), timedelta())
    if not any(backing.sessions for backing in backings) or length <= timedelta():
        return None
    return sum((backing.covered for backing in backings), timedelta()) / length
