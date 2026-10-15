from chronata.use_cases import typed_input
from chronata.use_cases.outcome import Outcome
from chronata.wiring import App


def configure(args, app: App) -> Outcome:
    day = app.log.working_day
    lunch_now = f"{day.lunch_start:%H:%M} for {day.lunch_minutes} min"
    shift_now = f"{day.shift_start:%H:%M} to {day.shift_end:%H:%M}"
    print("Press Enter to keep what is in brackets.")
    lunch_answer = input(f"{typed_input.LUNCH_QUESTION} [{lunch_now}] ").strip() or lunch_now
    shift_answer = input(f"{typed_input.SHIFT_QUESTION} [{shift_now}] ").strip() or shift_now
    label_answer = input(f"{typed_input.DEFAULT_LABEL_QUESTION} [{day.default_label or 'none'}] ").strip() or None
    return app.setup.configure(lunch_answer, shift_answer, label_answer)


def register(commands) -> None:
    command = commands.add_parser("setup", help="set your shift, lunch and main client or project")
    command.set_defaults(run=configure)
