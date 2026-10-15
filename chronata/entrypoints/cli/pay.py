from chronata.use_cases.outcome import Outcome
from chronata.wiring import App


def paid(args, app: App) -> Outcome:
    return app.payments.record(args.from_date, args.to_date, args.hours, args.time_off, args.ref)


def register(commands) -> None:
    command = commands.add_parser("paid", help="record what a payslip shows for overtime in a pay period")
    command.add_argument("from_date", metavar="from")
    command.add_argument("to_date", metavar="to")
    command.add_argument("hours", type=float, help="overtime hours the payslip pays (0 if none)")
    command.add_argument("--time-off", action="store_true", help="compensated with leave instead of pay")
    command.add_argument("--ref", help="e.g. 'payslip October 2026'")
    command.set_defaults(run=paid)
