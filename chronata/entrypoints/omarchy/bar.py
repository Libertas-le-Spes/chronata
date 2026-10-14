from chronata.entrypoints.web.server import DEFAULT_PORT, page_url
from chronata.timekeeping.durations import hours
from chronata.timekeeping.shifts import labels, open_shift
from chronata.use_cases.outcome import UserError
from chronata.use_cases.timesheet import Timesheet

CLOCK_ICON = ""
WARNING_ICON = ""


def status(sheet: Timesheet) -> dict:
    interrupted = sheet.interrupted()
    if interrupted:
        return {
            "text": WARNING_ICON,
            "tooltip": f"Still clocked in from {interrupted.shift.start:%a %H:%M}, before the PC last turned off.\nRight-click to open Chronata and close that shift.",
            "state": "interrupted",
        }
    current = open_shift(sheet.shifts())
    if current:
        worked = hours(current.worked(sheet.clock()))
        return {
            "text": f"{CLOCK_ICON}\n{worked}",
            "tooltip": f"Working since {current.start:%H:%M:%S}\nClick to clock out · right-click to open Chronata",
            "state": "in",
            "elapsed": worked,
        }
    return {"text": CLOCK_ICON, "tooltip": "Not clocked in\nClick to clock in · right-click to open Chronata", "state": "out"}


def toggle(app) -> None:
    sheet = app.sheet
    if sheet.interrupted():
        app.desktop.notify("Last shift is still open", "The PC turned off while you were clocked in. Right-click the timer to open Chronata and close it.")
        return
    all_shifts = sheet.shifts()
    clocked_in = open_shift(all_shifts) is not None
    if clocked_in and sheet.working_day.before_end_of_workday(sheet.clock()):
        app.desktop.open_page(page_url(DEFAULT_PORT) + "#confirm-out")
        return
    try:
        recent = labels(all_shifts)
        outcome = sheet.clock_out(None, None) if clocked_in else sheet.clock_in(None, None, recent[0] if recent else "")
    except UserError as error:
        app.desktop.notify("Could not log that", str(error))
        return
    app.desktop.notify(outcome.message.capitalize(), outcome.warning or "")
