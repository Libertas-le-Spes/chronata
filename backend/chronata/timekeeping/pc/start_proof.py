from dataclasses import dataclass

from chronata.timekeeping.pc.pc_sessions import PcSession
from chronata.timekeeping.record.stamps import Stamp
from chronata.timekeeping.shifts.shifts import Shift


@dataclass(frozen=True)
class StartProof:
    from_pc_on: bool
    entry: int
    stamps: tuple[Stamp, ...]


def start_proof(shift: Shift, sessions: list[PcSession], stamps: list[Stamp]) -> StartProof:
    pc_on = next((session for session in sessions if session.on == shift.first_start), None)
    entry = pc_on.first_entry if pc_on else shift.id
    return StartProof(pc_on is not None, entry, earliest_covering(stamps, entry))


def earliest_covering(stamps: list[Stamp], entry: int) -> tuple[Stamp, ...]:
    first: dict[str, Stamp] = {}
    for stamp in sorted(stamps, key=lambda s: s.time):
        if stamp.seq >= entry:
            first.setdefault(stamp.authority, stamp)
    return tuple(first.values())
