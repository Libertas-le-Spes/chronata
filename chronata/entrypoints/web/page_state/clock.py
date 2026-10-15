from datetime import datetime

from chronata.entrypoints.web.page_state.snapshot import Snapshot
from chronata.entrypoints.web.page_state.values import iso
from chronata.timekeeping.shifts import Shift
from chronata.timekeeping.today import day_so_far
from chronata.use_cases.pc_records import Interrupted


def state(app, taken: Snapshot) -> dict:
    current, now = taken.current, taken.now
    this_boot = app.pc.this_boot()
    return {
        "now": now.isoformat(),
        "open": _open(current, taken.shifts, now),
        "interrupted": _interrupted(taken.interrupted),
        "pcOnSince": iso(this_boot.on if this_boot else None),
        "unclockedSince": iso(app.clocking.unclocked_since()),
        "beforeEndOfWorkday": bool(current) and taken.hours.before_end_of_workday(current.label, now),
        "shiftEnd": _shift_end(taken, current),
    }


def _open(current: Shift | None, all_shifts: list[Shift], now: datetime) -> dict | None:
    if current is None:
        return None
    started, worked = day_so_far(all_shifts, now)
    return {"id": current.id, "label": current.label, "start": current.start.isoformat(), "dayStart": started.isoformat(),
            "workedSeconds": round(worked.total_seconds())}


def _interrupted(interrupted: Interrupted | None) -> dict | None:
    if interrupted is None:
        return None
    return {"start": interrupted.shift.start.isoformat(), "pcWentOff": iso(interrupted.pc_went_off)}


def _shift_end(taken: Snapshot, current: Shift | None) -> str | None:
    hours = taken.hours.for_label(current.label) if current else None
    return f"{hours.shift_end:%H:%M}" if hours else None
