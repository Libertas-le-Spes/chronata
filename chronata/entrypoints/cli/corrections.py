from chronata.entrypoints.cli.answers import answer_options, answers
from chronata.use_cases.outcome import Outcome
from chronata.wiring import App


def add(args, app: App) -> Outcome:
    return app.corrections.add(args.date, args.start, args.end, args.reason, args.note, args.label or "", answers(args))


def correct(args, app: App) -> Outcome:
    return app.corrections.correct(args.id, args.start, args.end, args.reason)


def strike(args, app: App) -> Outcome:
    return app.corrections.strike(args.id, args.reason)


def explain(args, app: App) -> Outcome:
    return app.corrections.explain_break(args.id, args.start, args.reason)


def register(commands) -> None:
    command = commands.add_parser("add", help="write down a whole shift after the fact")
    command.add_argument("date")
    command.add_argument("start")
    command.add_argument("end")
    command.add_argument("--reason", required=True, help="why it was not clocked at the time")
    command.add_argument("--note")
    command.add_argument("--label")
    answer_options(command)
    command.set_defaults(run=add)

    command = commands.add_parser("correct", help="fix a shift's times; the original stays on record")
    command.add_argument("id", type=int)
    command.add_argument("--start")
    command.add_argument("--end")
    command.add_argument("--reason", required=True)
    command.set_defaults(run=correct)

    command = commands.add_parser("strike", help="strike out a shift entered by mistake; it stays on record")
    command.add_argument("id", type=int)
    command.add_argument("--reason", required=True)
    command.set_defaults(run=strike)

    command = commands.add_parser("explain", help="say why the PC was off during a shift")
    command.add_argument("id", type=int)
    command.add_argument("start", help="when the break started, as shown by `chronata shifts`")
    command.add_argument("reason")
    command.set_defaults(run=explain)
