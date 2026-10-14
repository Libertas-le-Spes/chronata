from chronata.desktop import notify, open_page
from chronata.report import hours
from chronata.shifts import labels, open_shift
from chronata.timesheet import Timesheet, UserError
from chronata.web.server import DEFAULT_PORT, page_url

CLOCK_ICON = ""
WARNING_ICON = ""


def status(sheet: Timesheet) -> dict:
    now = sheet.clock()
    interrupted = sheet.interrupted()
    if interrupted:
        return {
            "text": WARNING_ICON,
            "tooltip": f"Still clocked in from {interrupted.shift.start:%a %H:%M}, before the PC last turned off.\nRight-click to open the log and close that shift.",
            "class": "active",
            "state": "interrupted",
        }
    current = open_shift(sheet.shifts())
    if current:
        return {
            "text": f"{CLOCK_ICON}\n{hours(sheet.rules.worked(current.segments(now)))}",
            "tooltip": f"Working since {current.start:%H:%M:%S}\nClick to clock out · right-click to open the log",
            "class": "active",
            "state": "in",
            "elapsed": hours(sheet.rules.worked(current.segments(now))),
        }
    return {
        "text": CLOCK_ICON,
        "tooltip": "Not clocked in\nClick to clock in · right-click to open the log",
        "class": "",
        "state": "out",
    }


def toggle(sheet: Timesheet) -> None:
    if sheet.interrupted():
        notify("Last shift is still open", "The PC turned off while you were clocked in. Right-click the timer to open the log and close it.")
        return
    all_shifts = sheet.shifts()
    if open_shift(all_shifts) and sheet.rules.before_end_of_workday(sheet.clock()):
        open_page(page_url(DEFAULT_PORT) + "#confirm-out")
        return
    try:
        recent = labels(all_shifts)
        outcome = sheet.clock_out(None, None) if open_shift(all_shifts) else sheet.clock_in(None, None, recent[0] if recent else "")
    except UserError as error:
        notify("Could not log that", str(error))
        return
    notify(outcome.message.capitalize(), outcome.warning or "")
