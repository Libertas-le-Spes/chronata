import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from chronata import bar, places, setup, verification
from chronata.places import PlaceBook, config_dir
from chronata.publisher import Publisher
from chronata.ledger import Ledger, TamperedLedger
from chronata.report import hours, report_lines, shift_lines
from chronata.settings import data_dir
from chronata.shifts import open_shift
from chronata.timesheet import Outcome, Timesheet, UserError


def clock_in(args, sheet: Timesheet) -> Outcome:
    return sheet.clock_in(args.at, args.note)


def clock_out(args, sheet: Timesheet) -> Outcome:
    return sheet.clock_out(args.at, args.note)


def add(args, sheet: Timesheet) -> Outcome:
    return sheet.add(args.date, args.start, args.end, args.reason, args.note)


def correct(args, sheet: Timesheet) -> Outcome:
    return sheet.correct(args.id, args.start, args.end, args.reason)


def strike(args, sheet: Timesheet) -> Outcome:
    return sheet.strike(args.id, args.reason)


def paid(args, sheet: Timesheet) -> Outcome:
    return sheet.record_payment(args.from_date, args.to_date, args.hours, args.time_off, args.ref)


def status(args, sheet: Timesheet) -> None:
    now = sheet.clock()
    current = open_shift(sheet.shifts())
    print(f"clocked in since {current.start:%Y-%m-%d %H:%M:%S}, {hours(now - current.start)} so far" if current else "not clocked in")
    this_week = [week for week in sheet.weeks() if week.start <= now.date() <= week.end]
    if this_week:
        print(f"this week: worked {hours(this_week[0].worked)}, overtime {hours(this_week[0].overtime)}")


def list_shifts(args, sheet: Timesheet) -> None:
    selected = [s for s in sheet.shifts() if _within(s.start.date(), args)]
    print("\n".join(shift_lines(selected, sheet.pc_sessions(), sheet.rules, sheet.clock())))


def report(args, sheet: Timesheet) -> None:
    selected = [week for week in sheet.weeks() if _within(week.start, args)]
    print("\n".join(report_lines(selected, sheet.reconciliation(selected), sheet.clock().date())))


def verify(args, sheet: Timesheet) -> None:
    if args.folder:
        sealed = verification.sealed_folder(Path(args.folder).expanduser())
        findings = verification.check(Ledger(sealed / "ledger.jsonl"), sealed)
        history = []
    else:
        findings = verification.check(sheet.ledger, sheet.directory)
        history = sheet.trail.rewrites("ledger.jsonl")
    problems = findings.problems + history
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise UserError("the log has been altered; see above")
    print(f"intact: {findings.entries} entries, each sealed to the one before" + ("" if args.folder else ", none rewritten in history"))
    if findings.stamps:
        latest = findings.latest_stamped
        by = ", ".join(f"{s.authority_name} {s.time:%Y-%m-%d %H:%M:%S} UTC" for s in findings.stamps if s.seq == latest)
        print(f"independently timestamped: everything up to entry {latest} existed by {by}")
        if findings.entries > latest:
            print(f"not yet timestamped: entries {latest + 1} to {findings.entries}")
    else:
        print("no independent timestamps yet")


def save(args, sheet: Timesheet) -> Outcome:
    return sheet.save_now()


def list_places(args, sheet: Timesheet) -> None:
    book = sheet.publish.book
    history = book.history()
    if not book.places():
        print("only saved on this computer; add a place with: chronata place-add KIND WHERE")
    for place in book.places():
        record = history.get(place.id, {})
        state = f"failed: {record['error']}" if record.get("error") else (f"saved {record['saved'][:19]}" if record.get("saved") else "not saved yet")
        print(f"{place.id:16} {places.KINDS[place.kind]:22} {place.name:14} {place.target}  [{state}]")


def add_place(args, sheet: Timesheet) -> Outcome:
    try:
        place = sheet.publish.book.add(args.kind, args.name or "", args.where, args.username or "", args.password or "")
    except places.SaveError as error:
        raise UserError(str(error))
    outcome = sheet.save_now()
    return Outcome(f"added {place.name} ({place.id}) and {outcome.message}", outcome.warning)


def remove_place(args, sheet: Timesheet) -> Outcome:
    try:
        place = sheet.publish.book.remove(args.id)
    except places.SaveError as error:
        raise UserError(str(error))
    return Outcome(f"removed {place.name}; copies already saved there are left as they are", None)


def configure(args, sheet: Timesheet) -> Outcome:
    rules = sheet.rules
    lunch_now = f"{rules.lunch_start:%H:%M} for {rules.lunch_minutes} min"
    shift_now = f"{rules.shift_start:%H:%M} to {rules.shift_end:%H:%M}"
    print("Press Enter to keep what is in brackets.")
    lunch_answer = input(f"{setup.LUNCH_QUESTION} [{lunch_now}] ").strip() or lunch_now
    shift_answer = input(f"{setup.SHIFT_QUESTION} [{shift_now}] ").strip() or shift_now
    return sheet.configure(lunch_answer, shift_answer)


def shutting_down(args, sheet: Timesheet) -> Outcome | None:
    stopping = subprocess.run(["systemctl", "is-system-running"], capture_output=True, text=True, check=False).stdout.strip()
    return sheet.record_shutdown() if stopping == "stopping" else None


def ui(args, sheet: Timesheet) -> None:
    from chronata.web.server import serve
    serve(sheet, args.port, open_browser=not args.no_browser)


def bar_status(args, sheet: Timesheet) -> None:
    print(json.dumps(bar.status(sheet)))


def bar_toggle(args, sheet: Timesheet) -> None:
    bar.toggle(sheet)


def service(args, sheet: Timesheet) -> None:
    from chronata.nudges import Nudges
    from chronata.web.server import page_url, serve_in_background
    if not serve_in_background(sheet, args.port):
        print(f"port {args.port} is taken; the page is served by whatever holds it", file=sys.stderr)
    Nudges(sheet, page_url(args.port)).run_forever()


def _within(day: date, args) -> bool:
    after = not args.from_date or day >= date.fromisoformat(args.from_date)
    before = not args.to_date or day <= date.fromisoformat(args.to_date)
    return after and before


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chronata", description="A sealed, append-only record of the time you work.")
    commands = parser.add_subparsers(required=True, metavar="command")

    command = commands.add_parser("in", help="clock in now")
    command.add_argument("--at", help="when you actually started, if you forgot (e.g. 08:04)")
    command.add_argument("--note")
    command.set_defaults(run=clock_in)

    command = commands.add_parser("out", help="clock out now")
    command.add_argument("--at", help="when you actually stopped, if you forgot (e.g. 18:42)")
    command.add_argument("--note", help="what kept you, who asked, where the evidence is")
    command.set_defaults(run=clock_out)

    command = commands.add_parser("add", help="write down a whole shift after the fact")
    command.add_argument("date")
    command.add_argument("start")
    command.add_argument("end")
    command.add_argument("--reason", required=True, help="why it was not clocked at the time")
    command.add_argument("--note")
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

    command = commands.add_parser("paid", help="record what a payslip shows for overtime in a pay period")
    command.add_argument("from_date", metavar="from")
    command.add_argument("to_date", metavar="to")
    command.add_argument("hours", type=float, help="overtime hours the payslip pays (0 if none)")
    command.add_argument("--time-off", action="store_true", help="compensated with leave instead of pay")
    command.add_argument("--ref", help="e.g. 'payslip October 2026'")
    command.set_defaults(run=paid)

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

    command = commands.add_parser("verify", help="prove the log has not been edited, and check its timestamps")
    command.add_argument("--folder", help="check a saved copy instead, e.g. an Obsidian vault or a folder")
    command.set_defaults(run=verify)

    command = commands.add_parser("save", help="timestamp the log and save it to every place now")
    command.set_defaults(run=save)

    command = commands.add_parser("places", help="where the log is saved")
    command.set_defaults(run=list_places)

    command = commands.add_parser("place-add", help="save the log somewhere else too")
    command.add_argument("kind", choices=list(places.KINDS))
    command.add_argument("where", help="a folder path, a git URL or a web server address")
    command.add_argument("--name")
    command.add_argument("--username")
    command.add_argument("--password")
    command.set_defaults(run=add_place)

    command = commands.add_parser("place-remove", help="stop saving to a place")
    command.add_argument("id")
    command.set_defaults(run=remove_place)

    command = commands.add_parser("ui", help="open the log in your browser")
    command.add_argument("--port", type=int, default=47630)
    command.add_argument("--no-browser", action="store_true")
    command.set_defaults(run=ui)

    command = commands.add_parser("setup", help="set your shift and lunch")
    command.set_defaults(run=configure)

    command = commands.add_parser("shutting-down", help="record the exact moment the PC shuts down (run by the service)")
    command.set_defaults(run=shutting_down)

    command = commands.add_parser("bar", help="status for the desktop bar, as JSON")
    command.set_defaults(run=bar_status)

    command = commands.add_parser("toggle", help="clock in or out now, with a desktop notification")
    command.set_defaults(run=bar_toggle)

    command = commands.add_parser("service", help="run in the background: the page, PC on/off records and reminders")
    command.add_argument("--port", type=int, default=47630)
    command.set_defaults(run=service)
    return parser


def open_timesheet() -> Timesheet:
    sheet = Timesheet(data_dir())
    sheet.publish = Publisher(PlaceBook(config_dir(), sheet.trail))
    return sheet


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        outcome = args.run(args, open_timesheet())
    except (UserError, TamperedLedger, FileNotFoundError) as error:
        print(f"chronata: {error}", file=sys.stderr)
        return 1
    if isinstance(outcome, Outcome):
        print(outcome.message)
        if outcome.warning:
            print(outcome.warning, file=sys.stderr)
    return 0
