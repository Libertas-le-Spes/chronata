import json

from chronata.entrypoints.bar import clock_button
from chronata.entrypoints.web.server import DEFAULT_PORT
from chronata.use_cases.log.outcome import Outcome
from chronata.wiring import App


def ui(args, app: App) -> None:
    from chronata.entrypoints.web.server import serve
    serve(app, args.port, open_browser=not args.no_browser)


def bar_status(args, app: App) -> None:
    print(json.dumps(clock_button.status(app)))


def bar_toggle(args, app: App) -> None:
    clock_button.toggle(app)


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

    command = commands.add_parser("service", help="run in the background: the page, PC on/off records and reminders")
    command.add_argument("--port", type=int, default=DEFAULT_PORT)
    command.set_defaults(run=service)

    command = commands.add_parser("shutting-down", help="record the exact moment the PC shuts down (run by the service)")
    command.set_defaults(run=shutting_down)
