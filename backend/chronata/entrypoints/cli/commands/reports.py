from datetime import date

from chronata.presenters.text.text_report import entry_lines, report_lines
from chronata.timekeeping.shifts.day_entries import day_entries
from chronata.timekeeping.shifts.durations import hours
from chronata.timekeeping.shifts.today import day_so_far
from chronata.wiring import App


def status(args, app: App) -> None:
    now = app.log.clock()
    print(_today(day_so_far(app.log.shifts(), now)))
    this_week = [week for week in app.log.weeks() if week.start <= now.date() <= week.end]
    if this_week:
        print(f"this week: worked {hours(this_week[0].worked)}, overtime {hours(this_week[0].overtime)}")


def _today(so_far) -> str:
    if so_far is None:
        return "not clocked in"
    started, worked = so_far
    return f"clocked in, {hours(worked)} today since {started:%Y-%m-%d %H:%M:%S}"


def list_shifts(args, app: App) -> None:
    selected = [entry for entry in day_entries(app.log.shifts()) if _within(entry.day, args)]
    print("\n".join(entry_lines(selected, app.log.pc_sessions(), app.timestamper.stamps(), app.log.clock())))


def report(args, app: App) -> None:
    per_label = {label: [week for week in label_weeks if _within(week.start, args)] for label, label_weeks in app.log.weeks_per_label().items()}
    print("\n".join(report_lines(per_label, app.log.compensation(per_label), app.log.clock().date())))


def _within(day: date, args) -> bool:
    after = not args.from_date or day >= date.fromisoformat(args.from_date)
    before = not args.to_date or day <= date.fromisoformat(args.to_date)
    return after and before


def register(commands) -> None:
    command = commands.add_parser("status", help="are you clocked in, and this week so far")
    command.set_defaults(run=status)

    for name, run, help_text in [
        ("shifts", list_shifts, "every shift with its corrections and flags"),
        ("report", report, "overtime per week and whether it was compensated"),
    ]:
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--from", dest="from_date")
        command.add_argument("--to", dest="to_date")
        command.set_defaults(run=run)
