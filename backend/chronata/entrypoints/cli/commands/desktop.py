import argparse
import json

from chronata.entrypoints.bar import clock_button
from chronata.entrypoints.web.address import DEFAULT_PORT
from chronata.entrypoints.web.page_door import PageDoor
from chronata.use_cases.log.outcome import Outcome
from chronata.wiring import App

MOST_IDLE_SECONDS = 24 * 60 * 60


def ui(args, app: App) -> None:
    from chronata.entrypoints.web.server import serve
    serve(app, args.port, open_browser=not args.no_browser)


def bar_status(args, app: App) -> None:
    print(json.dumps(clock_button.status(app)))


def bar_toggle(args, app: App) -> None:
    clock_button.toggle(app, PageDoor(app.desktop, DEFAULT_PORT, app.running))


def idle_seconds(text: str) -> int:
    try:
        seconds = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not a whole number of seconds")
    if not 0 <= seconds <= MOST_IDLE_SECONDS:
        raise argparse.ArgumentTypeError(f"idle time has to be between 0 and {MOST_IDLE_SECONDS} seconds")
    return seconds


def away(args, app: App) -> None:
    app.away.began(args.idle_seconds)


def back(args, app: App) -> None:
    app.away.ended()


def service(args, app: App) -> None:
    from chronata.entrypoints.service.background_service import run
    run(app, args.port)


def shutting_down(args, app: App) -> Outcome | None:
    return app.pc.record_shutdown() if app.power.shutting_down() else None


def register(commands) -> None:
    command = commands.add_parser("ui", help="open the log in your browser")
    command.add_argument("--port", type=int, default=DEFAULT_PORT)
    command.add_argument("--no-browser", action="store_true")
    command.set_defaults(run=ui)

    command = commands.add_parser("bar", help="status for the desktop bar, as JSON")
    command.set_defaults(run=bar_status)

    command = commands.add_parser("toggle", help="clock in or out from the bar")
    command.set_defaults(run=bar_toggle)

    command = commands.add_parser("away", help="note that the PC has had no input, so the bar can ask about it (run by the bar)")
    command.add_argument("idle_seconds", type=idle_seconds, help="how long there has been no input, up to a day")
    command.set_defaults(run=away)

    command = commands.add_parser("back", help="note that input has come back after being away (run by the bar)")
    command.set_defaults(run=back)

    command = commands.add_parser("service", help="run in the background: the page, PC on/off records and reminders")
    command.add_argument("--port", type=int, default=DEFAULT_PORT)
    command.set_defaults(run=service)

    command = commands.add_parser("shutting-down", help="record the exact moment the PC shuts down (run by the service)")
    command.set_defaults(run=shutting_down)
