from datetime import datetime

from chronata.presenters.page.facts import PageFacts
from chronata.presenters.page.values import iso
from chronata.timekeeping.shifts.shifts import Shift
from chronata.timekeeping.shifts.today import day_so_far
from chronata.use_cases.pc.pc_records import Interrupted


def state(facts: PageFacts) -> dict:
    current, now = facts.current, facts.now
    this_boot = facts.this_boot
    return {
        "now": now.isoformat(),
        "open": _open(current, facts.shifts, now),
        "interrupted": _interrupted(facts.interrupted),
        "pcOnSince": iso(this_boot.on if this_boot else None),
        "unclockedSince": iso(facts.unclocked_since),
        "beforeEndOfWorkday": bool(current) and facts.hours.before_end_of_workday(current.label, now),
        "shiftEnd": _shift_end(facts, current),
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


def _shift_end(facts: Snapshot, current: Shift | None) -> str | None:
    hours = facts.hours.for_label(current.label) if current else None
    return f"{hours.shift_end:%H:%M}" if hours else None
