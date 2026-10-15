from chronata.use_cases.outcome import Outcome
from chronata.wiring import App


def compensation(args, app: App) -> Outcome:
    return app.compensations.record(args.label or "", args.from_date, args.to_date, args.hours, args.time_off, args.ref, args.new_label)


def register(commands) -> None:
    command = commands.add_parser("compensation", help="record what was paid or given as time off for overtime in a period")
    command.add_argument("from_date", metavar="from")
    command.add_argument("to_date", metavar="to")
    command.add_argument("hours", type=float, help="overtime hours compensated (0 if none)")
    command.add_argument("--label", help="the client or project that compensated it; your default label if left out")
    command.add_argument("--new-label", action="store_true", help="confirm a new label that looks like an existing one")
    command.add_argument("--time-off", action="store_true", help="compensated with leave instead of pay")
    command.add_argument("--ref", help="e.g. 'payslip October 2026'")
    command.set_defaults(run=compensation)
