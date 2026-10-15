from chronata.entrypoints.cli.answers import hours_options
from chronata.use_cases import typed_input
from chronata.use_cases.labelling import describe_hours
from chronata.use_cases.outcome import Outcome
from chronata.wiring import App


def configure(args, app: App) -> Outcome:
    label_hours = app.log.hours
    day = label_hours.main
    lunch_now = f"{day.lunch.start:%H:%M} for {day.lunch.minutes} min" if day and day.lunch else "none"
    shift_now = f"{day.shift_start:%H:%M} to {day.shift_end:%H:%M}" if day else typed_input.DEFAULT_SHIFT
    print("Press Enter to keep what is in brackets.")
    label_answer = input(f"{typed_input.DEFAULT_LABEL_QUESTION} [{label_hours.default_label or 'none'}] ").strip() or None
    shift_answer = input(f"{typed_input.SHIFT_QUESTION} [{shift_now}] ").strip() or shift_now
    lunch_answer = input(f"{typed_input.LUNCH_QUESTION} [{lunch_now}] ").strip() or lunch_now
    return app.setup.configure(lunch_answer, shift_answer, label_answer)


def label_hours(args, app: App) -> Outcome | None:
    if args.label is not None:
        return app.setup.set_hours(args.label, args.shift or "", args.lunch or "", args.no_set_hours)
    label_hours = app.log.hours
    for label in label_hours.labels():
        default = " (default)" if label == label_hours.default_label else ""
        print(f"{label + default:24} {describe_hours(label_hours.for_label(label))}")
    return None


def register(commands) -> None:
    command = commands.add_parser("setup", help="set your shift, lunch and main client or project")
    command.set_defaults(run=configure)

    command = commands.add_parser("hours", help="show every label's hours, or change one label's")
    command.add_argument("label", nargs="?")
    hours_options(command)
    command.set_defaults(run=label_hours)
