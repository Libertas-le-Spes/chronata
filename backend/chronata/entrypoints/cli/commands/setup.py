from chronata.entrypoints.cli.answers import hours_from, hours_options
from chronata.entrypoints.cli.typed_answers import ask_inputs
from chronata.use_cases.labels.labelling import describe_hours
from chronata.use_cases.log.outcome import Outcome, UserError
from chronata.use_cases.questions import typed_input
from chronata.use_cases.questions.questions import HOURS_INPUTS, Answers, filled_in, hours_values
from chronata.wiring import App


def configure(args, app: App) -> Outcome:
    label_hours = app.log.hours
    print("Type times as numbers, like 830 or 1730. Press Enter to keep what is in brackets.")
    label_answer = input(f"{typed_input.DEFAULT_LABEL_QUESTION} [{label_hours.default_label or 'none'}] ").strip() or None
    typed = ask_inputs(input, filled_in(HOURS_INPUTS, hours_values(label_hours.main)))
    return app.setup.configure(Answers(**typed), label_answer)


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
    return app.setup.set_hours(choice.label, hours_from(args, app.log.hours.for_label(choice.label)))


def register(commands) -> None:
    command = commands.add_parser("setup", help="set your shift, lunch and main client or project")
    command.set_defaults(run=configure)

    command = commands.add_parser("hours", help="show every label's hours, or change one label's")
    command.add_argument("label", nargs="?")
    hours_options(command)
    command.set_defaults(run=label_hours)
