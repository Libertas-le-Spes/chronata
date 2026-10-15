from chronata.entrypoints.cli.answers import hours_from, hours_options
from chronata.entrypoints.cli.hours_prompt import ask_hours
from chronata.use_cases.labels.labelling import describe_hours
from chronata.use_cases.log.outcome import Outcome, UserError
from chronata.use_cases.questions import typed_input
from chronata.wiring import App


def configure(args, app: App) -> Outcome:
    label_hours = app.log.hours
    print("Type times as numbers, like 830 or 1730. Press Enter to keep what is in brackets.")
    label_answer = input(f"{typed_input.DEFAULT_LABEL_QUESTION} [{label_hours.default_label or 'none'}] ").strip() or None
    shift_answer, lunch_answer = ask_hours(input, label_hours.main)
    return app.setup.configure(lunch_answer, shift_answer, label_answer)


def label_hours(args, app: App) -> Outcome | None:
    if args.label is not None:
        return _change_hours(args, app)
    label_hours = app.log.hours
    for label in label_hours.labels():
        default = " (default)" if label == label_hours.default_label else ""
        print(f"{label + default:24} {describe_hours(label_hours.for_label(label))}")
    return None


def _change_hours(args, app: App) -> Outcome:
    choice = app.labels.check(args.label)
    if not choice.exists:
        raise UserError(f"there is no label '{args.label.strip()}'; add it first")
    shift, lunch = hours_from(args, app.log.hours.for_label(choice.label))
    return app.setup.set_hours(choice.label, shift, lunch, args.no_set_hours)


def register(commands) -> None:
    command = commands.add_parser("setup", help="set your shift, lunch and main client or project")
    command.set_defaults(run=configure)

    command = commands.add_parser("hours", help="show every label's hours, or change one label's")
    command.add_argument("label", nargs="?")
    hours_options(command)
    command.set_defaults(run=label_hours)
