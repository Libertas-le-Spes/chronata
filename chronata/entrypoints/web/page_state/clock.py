from chronata.timekeeping.shifts import day_so_far
from chronata.entrypoints.web.page_state.snapshot import Snapshot


def state(app, taken: Snapshot) -> dict:
    current, interrupted, now = taken.current, taken.interrupted, taken.now
    today = day_so_far(taken.shifts, now)
    this_boot = app.pc.this_boot()
    unclocked = app.clocking.unclocked_since()
    return {
        "now": now.isoformat(),
        "open": {"id": current.id, "label": current.label, "start": current.start.isoformat(), "dayStart": today[0].isoformat(),
                 "workedSeconds": round(today[1].total_seconds())} if current else None,
        "interrupted": {
            "start": interrupted.shift.start.isoformat(),
            "pcWentOff": interrupted.pc_went_off.isoformat() if interrupted.pc_went_off else None,
        } if interrupted else None,
        "pcOnSince": this_boot.on.isoformat() if this_boot else None,
        "unclockedSince": unclocked.isoformat() if unclocked else None,
        "beforeEndOfWorkday": taken.working_day.before_end_of_workday(now),
        "shiftEnd": f"{taken.working_day.shift_end:%H:%M}",
    }
