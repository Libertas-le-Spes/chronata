from chronata.use_cases.log.outcome import Outcome
from chronata.wiring import App


def waive(args, app: App) -> Outcome:
    return app.waivers.waive([args.id], args.start, args.end, args.reason)


def withdraw(args, app: App) -> Outcome:
    return app.waivers.withdraw(args.id, args.start, args.reason)


def register(commands) -> None:
    command = commands.add_parser("waive", help="stop counting a stretch of a shift you were not working, such as after forgetting to clock out")
    command.add_argument("id", type=int)
    command.add_argument("start")
    command.add_argument("end")
    command.add_argument("--reason", required=True, help="why that time was not work")
    command.set_defaults(run=waive)

    command = commands.add_parser("unwaive", help="count a waived stretch again")
    command.add_argument("id", type=int)
    command.add_argument("start", help="when the waived stretch starts, as shown by `chronata shifts`")
    command.add_argument("--reason", required=True)
    command.set_defaults(run=withdraw)
