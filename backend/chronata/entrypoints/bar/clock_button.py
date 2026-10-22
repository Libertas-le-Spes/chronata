from datetime import datetime

from chronata.entrypoints.bar.clock_in_questions import ask_and_clock_in
from chronata.timekeeping.shifts.durations import hours
from chronata.timekeeping.shifts.shifts import Shift, open_shift
from chronata.timekeeping.shifts.today import day_so_far
from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.log.ports import Page
from chronata.use_cases.pc.pc_records import Interrupted

CLOCK_ICON = ""
WARNING_ICON = ""


def status(app) -> dict:
    interrupted = app.pc.interrupted()
    if interrupted:
        return _interrupted(interrupted)
    all_shifts = app.log.shifts()
    current = open_shift(all_shifts)
    if current:
        return _working(current, all_shifts, app.log.clock())
    return {"text": CLOCK_ICON, "tooltip": "Not clocked in\nClick to choose a label and clock in · right-click to open Chronata", "state": "out"}


def _interrupted(interrupted: Interrupted) -> dict:
    return {
        "text": WARNING_ICON,
        "tooltip": f"Still clocked in from {interrupted.shift.start:%a %H:%M}, before the PC last turned off.\nRight-click to open Chronata and close that shift.",
        "state": "interrupted",
    }


def _working(current: Shift, all_shifts: list[Shift], now: datetime) -> dict:
    started, so_far = day_so_far(all_shifts, now)
    worked = hours(so_far)
    on_label = f" on {current.label}" if current.label else ""
    return {
        "text": f"{CLOCK_ICON}\n{worked}",
        "tooltip": f"Working{on_label}, {worked} today since {started:%H:%M:%S}\nClick to clock out · right-click to open Chronata",
        "state": "in",
        "elapsed": worked,
    }


def toggle(app, page: Page) -> None:
    if app.pc.interrupted():
        app.desktop.notify("Last shift is still open", "The PC turned off while you were clocked in. Right-click the timer to open Chronata and close it.")
        return
    current = open_shift(app.log.shifts())
    if current is None:
        ask_and_clock_in(app, page)
        return
    if app.log.hours.before_end_of_workday(current.label, app.log.clock()):
        page.open("confirm-out")
        return
    try:
        outcome = app.clocking.clock_out(None, None)
    except UserError as error:
        app.desktop.notify("Could not clock out", str(error))
        return
    app.desktop.notify(outcome.headline, outcome.warning or "")
