from chronata.use_cases.outcome import Outcome
from chronata.wiring import App


def clock_in(args, app: App) -> Outcome:
    return app.clocking.clock_in(args.at, args.note, args.label, args.new_label, args.off_default)


def clock_out(args, app: App) -> Outcome:
    return app.clocking.clock_out(args.at, args.note)


def register(commands) -> None:
    command = commands.add_parser("in", help="clock in now, or carry on today's shift")
    command.add_argument("--at", help="when you actually started, if you forgot (e.g. 08:04)")
    command.add_argument("--label", help="client or project, e.g. 'Acme website'; each label gets its own folder")
    command.add_argument("--new-label", action="store_true", help="confirm a new label that looks like an existing one")
    command.add_argument("--off-default", action="store_true", help="confirm clocking in on a workday on a label other than the default")
    command.add_argument("--note")
    command.set_defaults(run=clock_in)

    command = commands.add_parser("out", help="clock out now")
    command.add_argument("--at", help="when you actually stopped, if you forgot (e.g. 18:42)")
    command.add_argument("--note", help="what kept you, who asked, where the evidence is")
    command.set_defaults(run=clock_out)
