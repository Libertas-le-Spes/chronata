from chronata.timekeeping.entries.clocking import ClockIn, ClockOut, ClockResumed
from chronata.timekeeping.entries.corrections import BreakExplained, ShiftAdded, ShiftCorrected, ShiftVoided
from chronata.timekeeping.entries.labels import ShiftLabelled
from chronata.timekeeping.entries.pc import PcOffBreak
from chronata.timekeeping.record.record import Entry
from chronata.timekeeping.shifts.shifts import Shift

SHIFT_CHANGES = {kind.kind: kind.apply for kind in (
    ClockIn, ClockOut, ClockResumed, PcOffBreak, BreakExplained, ShiftAdded, ShiftCorrected, ShiftLabelled, ShiftVoided,
)}


def shifts(entries: list[Entry]) -> list[Shift]:
    found: dict[int, Shift] = {}
    for entry in entries:
        change = SHIFT_CHANGES.get(entry.kind)
        if change is None:
            continue
        change(found, entry)
        if entry.data.get("note"):
            found[entry.data.get("shift", entry.seq)].notes.append(entry.data["note"])
    return sorted(found.values(), key=lambda shift: shift.start)
