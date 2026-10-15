from datetime import date

from chronata.presenters.text_report import entry_lines, report_lines
from chronata.timekeeping.day_entries import day_entries
from chronata.timekeeping.durations import hours
from chronata.timekeeping.shifts import completed, open_shift
from chronata.timekeeping.labels import worked_by_label
from chronata.wiring import App


def status(args, app: App) -> None:
    now = app.log.clock()
    current = open_shift(app.log.shifts())
    print(f"clocked in since {current.start:%Y-%m-%d %H:%M:%S}, {hours(current.worked(now))} so far" if current else "not clocked in")
    this_week = [week for week in app.log.weeks() if week.start <= now.date() <= week.end]
    if this_week:
        print(f"this week: worked {hours(this_week[0].worked)}, overtime {hours(this_week[0].overtime)}")


def list_shifts(args, app: App) -> None:
    selected = [entry for entry in day_entries(app.log.shifts()) if _within(entry.day, args)]
    print("\n".join(entry_lines(selected, app.log.pc_sessions(), app.timestamper.stamps(), app.log.clock())))


def report(args, app: App) -> None:
    selected = [week for week in app.log.weeks() if _within(week.start, args)]
    chosen = [s for s in completed(app.log.shifts()) if _within(s.start.date(), args)]
    print("\n".join(report_lines(selected, app.log.reconciliation(selected), app.log.clock().date(), worked_by_label(chosen))))


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
