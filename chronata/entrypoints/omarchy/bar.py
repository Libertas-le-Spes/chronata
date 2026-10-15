from chronata.entrypoints.web.server import DEFAULT_PORT, page_url
from chronata.timekeeping.durations import hours
from chronata.timekeeping.labels import known_labels
from chronata.timekeeping.shifts import open_shift
from chronata.use_cases.outcome import OffDefaultLabel, UnconfirmedLabel, UserError
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
        on_label = f" on {current.label}" if current.label else ""
        return {
            "text": f"{CLOCK_ICON}\n{worked}",
            "tooltip": f"Working{on_label} since {current.start:%H:%M:%S}\nClick to clock out · right-click to open Chronata",
            "state": "in",
            "elapsed": worked,
        }
    return {"text": CLOCK_ICON, "tooltip": "Not clocked in\nClick to choose a label and clock in · right-click to open Chronata", "state": "out"}


def toggle(app) -> None:
    sheet = app.sheet
    if sheet.interrupted():
        app.desktop.notify("Last shift is still open", "The PC turned off while you were clocked in. Right-click the timer to open Chronata and close it.")
        return
    all_shifts = sheet.shifts()
    if open_shift(all_shifts) is None:
        _ask_and_clock_in(app)
        return
    if sheet.working_day.before_end_of_workday(sheet.clock()):
        app.desktop.open_page(page_url(DEFAULT_PORT) + "#confirm-out")
        return
    try:
        outcome = sheet.clock_out(None, None)
    except UserError as error:
        app.desktop.notify("Could not clock out", str(error))
        return
    app.desktop.notify(outcome.message.capitalize(), outcome.warning or "")


def _ask_and_clock_in(app) -> None:
    sheet = app.sheet
    now = sheet.clock()
    pc_on = sheet.pc_on_since()
    known = known_labels(sheet.shifts())
    lines = ["Clock in on which client or project?",
             f"Your labels: {', '.join(known)}" if known else "",
             f"The PC has been on since {pc_on:%H:%M} ({hours(now - pc_on)})." if pc_on else ""]
    typed = app.desktop.ask("\n".join(line for line in lines if line), sheet.suggested_label())
    if typed is None:
        return
    since = sheet.unclocked_since()
    if since is None:
        _clock_in_on(app, typed)
        return
    from_pc_on = f"Since {since:%H:%M}"
    question = f"Have you been working since the PC came on at {since:%H:%M} ({hours(now - since)} ago), or are you starting now?"
    picked = app.desktop.choose(question, [from_pc_on, "From now"])
    if picked == from_pc_on:
        _clock_in_on(app, typed, since.isoformat(), "started when the PC came on")
    elif picked:
        _clock_in_on(app, typed)


def _clock_in_on(app, label: str, at: str | None = None, note: str | None = None, new_label: bool = False, off_default: bool = False) -> None:
    try:
        outcome = app.sheet.clock_in(at, note, label, new_label, off_default)
    except UnconfirmedLabel as error:
        create = f"Create “{error.label}”"
        question = f"“{error.label}” would start a new label, with its own folder. Did you mean {' or '.join(error.near_misses)}?"
        picked = app.desktop.choose(question, [*error.near_misses, create])
        if picked == create:
            _clock_in_on(app, error.label, at, note, True, off_default)
        elif picked:
            _clock_in_on(app, picked, at, note, new_label, off_default)
        return
    except OffDefaultLabel as error:
        chosen = f"Clock in on {error.label}" if error.label else "Clock in with no label"
        question = f"Today is a workday, and {error.default_label} is your default. {chosen} instead?"
        picked = app.desktop.choose(question, [f"Use {error.default_label}", chosen])
        if picked == chosen:
            _clock_in_on(app, label, at, note, new_label, True)
        elif picked:
            _clock_in_on(app, error.default_label, at, note)
        return
    except UserError as error:
        app.desktop.notify("Could not clock in", str(error))
        return
    app.desktop.notify(outcome.message.capitalize(), outcome.warning or "")
