from chronata.presenters.readable_copy import label_folder
from chronata.timekeeping.durations import hours
from chronata.entrypoints.cli.answers import answer_options, answers
from chronata.timekeeping.labels import hours_by_label
from chronata.use_cases.outcome import Outcome
from chronata.wiring import App


def label(args, app: App) -> Outcome:
    return app.labels.label_shift(args.id, args.label, answers(args))


def list_labels(args, app: App) -> None:
    summary = hours_by_label(app.log.shifts(), app.log.clock())
    if not summary:
        print("no labels yet; add one with: chronata in --label NAME")
    default = app.log.hours.default_label
    for row in summary:
        running = "  (shift still open)" if row.open_now else ""
        marked = f"{row.label} (default)" if row.label and row.label == default else row.label or "(no label)"
        print(f"{marked:24} folder {label_folder(row.label):24} this week {hours(row.this_week):>6}   all time {hours(row.all_time):>7}{running}")


def add_label(args, app: App) -> Outcome:
    return app.labels.create(args.label, answers(args))


def rename_label(args, app: App) -> Outcome:
    return app.labels.rename(args.old, args.new, answers(args))


def default_label(args, app: App) -> Outcome | None:
    if args.label is not None:
        return app.labels.set_default(args.label, answers(args))
    default = app.log.hours.default_label
    print(default or "no default label; set one with: chronata default-label NAME")
    return None


def register(commands) -> None:
    command = commands.add_parser("label", help="set or change a shift's client or project")
    command.add_argument("id", type=int)
    command.add_argument("label", help="the label, or '' to remove it")
    answer_options(command)
    command.set_defaults(run=label)

    command = commands.add_parser("labels", help="every label with its folder and hours")
    command.set_defaults(run=list_labels)

    command = commands.add_parser("label-add", help="add a client or project with its own hours")
    command.add_argument("label")
    answer_options(command)
    command.set_defaults(run=add_label)

    command = commands.add_parser("label-rename", help="rename a label on every shift; renaming onto an existing label merges them")
    command.add_argument("old")
    command.add_argument("new")
    answer_options(command)
    command.set_defaults(run=rename_label)

    command = commands.add_parser("default-label", help="show or set your main client or project; on workdays clocking in on another asks first")
    command.add_argument("label", nargs="?", help="the label, or '' to have no default")
    answer_options(command)
    command.set_defaults(run=default_label)
