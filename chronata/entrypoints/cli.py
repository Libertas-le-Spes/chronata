import argparse
import json
import sys
from datetime import date
from pathlib import Path

from chronata.entrypoints import clock_button
from chronata.entrypoints.web.server import DEFAULT_PORT
from chronata.presenters.readable_copy import label_folder
from chronata.presenters.text_report import report_lines, shift_lines
from chronata.timekeeping.durations import hours
from chronata.timekeeping.labels import hours_by_label
from chronata.timekeeping.record import TamperedRecord
from chronata.timekeeping.shifts import completed, open_shift
from chronata.timekeeping.working_day import worked_by_label
from chronata.use_cases import typed_input
from chronata.use_cases.outcome import OffDefaultLabel, Outcome, UnconfirmedLabel, UserError
from chronata.use_cases.verification import verify
from chronata.wiring import App, open_app, open_saved_copy


def clock_in(args, app: App) -> Outcome:
    return app.sheet.clock_in(args.at, args.note, args.label, args.new_label, args.off_default)


def clock_out(args, app: App) -> Outcome:
    return app.sheet.clock_out(args.at, args.note)


def add(args, app: App) -> Outcome:
    return app.sheet.add(args.date, args.start, args.end, args.reason, args.note, args.label or "", args.new_label)


def correct(args, app: App) -> Outcome:
    return app.sheet.correct(args.id, args.start, args.end, args.reason)


def label(args, app: App) -> Outcome:
    return app.sheet.label(args.id, args.label, args.new_label)


def list_labels(args, app: App) -> None:
    summary = hours_by_label(app.sheet.shifts(), app.sheet.clock())
    if not summary:
        print("no labels yet; add one with: chronata in --label NAME")
    default = app.sheet.working_day.default_label
    for row in summary:
        running = "  (shift still open)" if row.open_now else ""
        marked = f"{row.label} (default)" if row.label and row.label == default else row.label or "(no label)"
        print(f"{marked:24} folder {label_folder(row.label):24} this week {hours(row.this_week):>6}   all time {hours(row.all_time):>7}{running}")


def default_label(args, app: App) -> Outcome | None:
    if args.label is not None:
        return app.sheet.set_default_label(args.label, args.new_label)
    default = app.sheet.working_day.default_label
    print(default or "no default label; set one with: chronata default-label NAME")
    return None


def rename_label(args, app: App) -> Outcome:
    return app.sheet.rename_label(args.old, args.new, args.new_label)


def strike(args, app: App) -> Outcome:
    return app.sheet.strike(args.id, args.reason)


def paid(args, app: App) -> Outcome:
    return app.sheet.record_payment(args.from_date, args.to_date, args.hours, args.time_off, args.ref)


def explain(args, app: App) -> Outcome:
    return app.sheet.explain_break(args.id, args.start, args.reason)


def status(args, app: App) -> None:
    now = app.sheet.clock()
    current = open_shift(app.sheet.shifts())
    print(f"clocked in since {current.start:%Y-%m-%d %H:%M:%S}, {hours(current.worked(now))} so far" if current else "not clocked in")
    this_week = [week for week in app.sheet.weeks() if week.start <= now.date() <= week.end]
    if this_week:
        print(f"this week: worked {hours(this_week[0].worked)}, overtime {hours(this_week[0].overtime)}")


def list_shifts(args, app: App) -> None:
    selected = [s for s in app.sheet.shifts() if _within(s.start.date(), args)]
    print("\n".join(shift_lines(selected, app.sheet.pc_sessions(), app.timestamper.stamps(), app.sheet.clock())))


def report(args, app: App) -> None:
    selected = [week for week in app.sheet.weeks() if _within(week.start, args)]
    chosen = [s for s in completed(app.sheet.shifts()) if _within(s.start.date(), args)]
    print("\n".join(report_lines(selected, app.sheet.reconciliation(selected), app.sheet.clock().date(), worked_by_label(chosen))))


def check(args, app: App) -> None:
    if args.folder:
        record, timestamper = open_saved_copy(Path(args.folder).expanduser())
        findings = verify(record, timestamper)
    else:
        findings = verify(app.sheet.record, app.timestamper, app.history)
    if findings.problems:
        print("\n".join(findings.problems), file=sys.stderr)
        raise UserError("the log has been altered; see above")
    kept = not args.folder and app.history.keeps_history()
    counted = f"{findings.entries} {'entry' if findings.entries == 1 else 'entries'}"
    print(f"intact: {counted}, each sealed to the one before" + (", none rewritten in history" if kept else ""))
    newest = findings.latest_stamped
    if newest is None:
        print("no independent timestamps yet")
        return
    by = ", ".join(f"{s.authority_name} {s.time:%Y-%m-%d %H:%M:%S} UTC" for s in findings.stamps if s.seq == newest)
    print(f"independently timestamped: everything up to entry {newest} existed by {by}")
    if findings.entries > newest:
        print(f"not yet timestamped: entries {newest + 1} to {findings.entries}")


def save(args, app: App) -> Outcome:
    return app.sheet.save_now()


def list_places(args, app: App) -> None:
    statuses = app.saving.statuses()
    if not statuses:
        print("only saved on this computer; add a place with: chronata place-add KIND WHERE")
    kinds = app.saving.places.kinds()
    for place, last in statuses:
        state = f"failed: {last['error']}" if last.get("error") else (f"saved {last['saved'][:19]}" if last.get("saved") else "not saved yet")
        print(f"{place.id:16} {kinds[place.kind]:22} {place.name:14} {place.target}  [{state}]")


def add_place(args, app: App) -> Outcome:
    return app.saving.add_place(app.sheet, args.kind, args.name or "", args.where, args.username or "", args.password or "", args.folder or "")


def remove_place(args, app: App) -> Outcome:
    return app.saving.remove_place(args.id)


def configure(args, app: App) -> Outcome:
    day = app.sheet.working_day
    lunch_now = f"{day.lunch_start:%H:%M} for {day.lunch_minutes} min"
    shift_now = f"{day.shift_start:%H:%M} to {day.shift_end:%H:%M}"
    print("Press Enter to keep what is in brackets.")
    lunch_answer = input(f"{typed_input.LUNCH_QUESTION} [{lunch_now}] ").strip() or lunch_now
    shift_answer = input(f"{typed_input.SHIFT_QUESTION} [{shift_now}] ").strip() or shift_now
    label_answer = input(f"{typed_input.DEFAULT_LABEL_QUESTION} [{day.default_label or 'none'}] ").strip() or None
    return app.sheet.configure(lunch_answer, shift_answer, label_answer)


def shutting_down(args, app: App) -> Outcome | None:
    return app.sheet.record_shutdown() if app.power.shutting_down() else None


def ui(args, app: App) -> None:
    from chronata.entrypoints.web.server import serve
    serve(app, args.port, open_browser=not args.no_browser)


def bar_status(args, app: App) -> None:
    print(json.dumps(clock_button.status(app.sheet)))


def bar_toggle(args, app: App) -> None:
    clock_button.toggle(app)


def service(args, app: App) -> None:
    from chronata.entrypoints.background_service import run
    run(app, args.port, with_tray=not args.no_tray)


def _within(day: date, args) -> bool:
    after = not args.from_date or day >= date.fromisoformat(args.from_date)
    before = not args.to_date or day <= date.fromisoformat(args.to_date)
    return after and before


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chronata", description="A sealed, timestamped record of the time you work.")
    commands = parser.add_subparsers(required=True, metavar="command")

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

    command = commands.add_parser("add", help="write down a whole shift after the fact")
    command.add_argument("date")
    command.add_argument("start")
    command.add_argument("end")
    command.add_argument("--reason", required=True, help="why it was not clocked at the time")
    command.add_argument("--note")
    command.add_argument("--label")
    command.add_argument("--new-label", action="store_true", help="confirm a new label that looks like an existing one")
    command.set_defaults(run=add)

    command = commands.add_parser("label", help="set or change a shift's client or project")
    command.add_argument("id", type=int)
    command.add_argument("label", help="the label, or '' to remove it")
    command.add_argument("--new-label", action="store_true", help="confirm a new label that looks like an existing one")
    command.set_defaults(run=label)

    command = commands.add_parser("labels", help="every label with its folder and hours")
    command.set_defaults(run=list_labels)

    command = commands.add_parser("label-rename", help="rename a label on every shift; renaming onto an existing label merges them")
    command.add_argument("old")
    command.add_argument("new")
    command.add_argument("--new-label", action="store_true", help="confirm a new name that looks like an existing label")
    command.set_defaults(run=rename_label)

    command = commands.add_parser("default-label", help="show or set your main client or project; on workdays clocking in on another asks first")
    command.add_argument("label", nargs="?", help="the label, or '' to have no default")
    command.add_argument("--new-label", action="store_true", help="confirm a new label that looks like an existing one")
    command.set_defaults(run=default_label)

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
    command.set_defaults(run=check)

    command = commands.add_parser("save", help="timestamp the log and save it to every place now")
    command.set_defaults(run=save)

    command = commands.add_parser("places", help="where the log is saved")
    command.set_defaults(run=list_places)

    command = commands.add_parser("place-add", help="save the log somewhere else too")
    command.add_argument("kind", choices=["obsidian", "folder", "git", "git-folder", "webdav"])
    command.add_argument("where", help="a folder path, a git URL or a web server address")
    command.add_argument("--folder", help="for git-folder: the folder inside the repository, e.g. 'Work Logs'")
    command.add_argument("--name")
    command.add_argument("--username")
    command.add_argument("--password")
    command.set_defaults(run=add_place)

    command = commands.add_parser("place-remove", help="stop saving to a place")
    command.add_argument("id")
    command.set_defaults(run=remove_place)

    command = commands.add_parser("ui", help="open the log in your browser")
    command.add_argument("--port", type=int, default=DEFAULT_PORT)
    command.add_argument("--no-browser", action="store_true")
    command.set_defaults(run=ui)

    command = commands.add_parser("setup", help="set your shift, lunch and main client or project")
    command.set_defaults(run=configure)

    command = commands.add_parser("shutting-down", help="record the exact moment the PC shuts down (run by the service)")
    command.set_defaults(run=shutting_down)

    command = commands.add_parser("bar", help="status for the desktop bar, as JSON")
    command.set_defaults(run=bar_status)

    command = commands.add_parser("toggle", help="clock in or out from the bar")
    command.set_defaults(run=bar_toggle)

    command = commands.add_parser("service", help="run in the background: the page, PC on/off records, reminders and the tray icon")
    command.add_argument("--port", type=int, default=DEFAULT_PORT)
    command.add_argument("--no-tray", action="store_true", help="leave out the tray icon, e.g. when a bar widget does its job")
    command.set_defaults(run=service)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        outcome = args.run(args, open_app())
    except UnconfirmedLabel as error:
        print(f"chronata: {error} Add --new-label to confirm.", file=sys.stderr)
        return 1
    except OffDefaultLabel as error:
        print(f"chronata: {error} Add --off-default to confirm.", file=sys.stderr)
        return 1
    except (UserError, TamperedRecord, FileNotFoundError) as error:
        print(f"chronata: {error}", file=sys.stderr)
        return 1
    if isinstance(outcome, Outcome):
        print(outcome.message)
        if outcome.warning:
            print(outcome.warning, file=sys.stderr)
    return 0
