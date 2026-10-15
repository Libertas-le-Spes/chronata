from datetime import datetime, timedelta

from chronata.timekeeping.pc.pc_sessions import PcSession, support
from chronata.timekeeping.pc.start_proof import StartProof, start_proof
from chronata.timekeeping.record.stamps import Stamp
from chronata.timekeeping.shifts.durations import hours
from chronata.timekeeping.shifts.shifts import Shift

LATE_ENOUGH_TO_FLAG = timedelta(minutes=15)


def piece_lines(piece: Shift, sessions: list[PcSession], stamps: list[Stamp], now: datetime) -> list[str]:
    proof = start_proof(piece, sessions, stamps)
    span = f"{piece.start:%H:%M:%S}–{piece.end:%H:%M:%S} ({hours(piece.worked(piece.end))})" if piece.end else f"{piece.start:%H:%M:%S}–now"
    lines = [f"shift {piece.id}, {span}" + (", marked as a mistake" if piece.voided else ""), started(proof, piece.start)]
    if piece.entered_late_by > LATE_ENOUGH_TO_FLAG:
        lines.append("written down later, from the PC-on time" if proof.from_pc_on else f"entered {_ago(piece.entered_late_by)} after the fact")
    lines.append(pc_support(piece, sessions, now))
    lines += [f"note: {note}" for note in piece.notes]
    return lines + piece.changes


def started(proof: StartProof, start: datetime) -> str:
    source = f"started when the PC came on at {start:%H:%M:%S}" if proof.from_pc_on else f"start logged in entry {proof.entry}"
    if not proof.stamps:
        return f"{source} · not yet independently timestamped"
    local = [(stamp.authority_name, stamp.time.astimezone(start.tzinfo)) for stamp in proof.stamps]
    shown = ", ".join(f"{name} {moment:%H:%M:%S}" if moment.date() == start.date() else f"{name} {moment:%Y-%m-%d %H:%M:%S}" for name, moment in local)
    return f"{source} · independently timestamped by {shown}"


def pc_support(shift: Shift, sessions: list[PcSession], now: datetime) -> str:
    backing = support(shift.start, shift.end, sessions, now)
    if not backing.sessions:
        return "PC: no record (before PC records begin)" if backing.before_records else "PC: off for the whole shift"
    spans = ", ".join(f"{s.on:%a %H:%M}–{_off(s)}" for s in backing.sessions)
    return f"PC: on for {backing.share:.0%} of the shift ({spans})"


def _off(session: PcSession) -> str:
    if session.off is None:
        return "still on"
    return f"{session.off:%a %H:%M:%S} shutdown" if session.exact else f"{session.off:%a %H:%M} last activity"


def _ago(span: timedelta) -> str:
    if span >= timedelta(days=1):
        return f"{span.days}d {span.seconds // 3600}h"
    return hours(span) + "h"
