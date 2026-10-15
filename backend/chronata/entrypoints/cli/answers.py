from dataclasses import replace

from chronata.entrypoints.cli.typed_answers import ask_inputs
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.use_cases.questions.questions import HOURS_INPUTS, Answers, Choice, Question, filled_in, hours_values


def hours_options(command) -> None:
    for needed in HOURS_INPUTS:
        command.add_argument("--" + needed.name.replace("_", "-"), help=f"{needed.prompt.lower()}, e.g. {needed.example}")
    command.add_argument("--no-set-hours", action="store_true", help="no shift times: only the time worked is counted")


def answer_options(command) -> None:
    hours_options(command)
    command.add_argument("--new-label", action="store_true", help="confirm a new label that looks like an existing one")
    command.set_defaults(off_default=False)


def clock_in_options(command) -> None:
    answer_options(command)
    command.add_argument("--off-default", action="store_true", help="confirm working on a label other than the default on a workday")


def hours_from(args, current: WorkingDay | None) -> Answers:
    given = answers(args)
    if args.no_set_hours or any(getattr(args, needed.name) for needed in HOURS_INPUTS):
        return given
    return replace(given, **ask_inputs(input, filled_in(HOURS_INPUTS, hours_values(current))))


def answers(args) -> Answers:
    return Answers.from_dict({name: value for name, value in vars(args).items() if value is not None})


def how_to_answer(question: Question) -> str:
    return "\n".join([question.text, *(f"  {choice.caption}: {_options(choice)}" for choice in question.choices)])


def _options(choice: Choice) -> str:
    relabel = [f"give '{choice.label}' as the label"] if choice.label is not None else []
    flags = [_flag(name, value) for name, value in choice.answers.items()]
    inputs = [_flag(needed.name, needed.example) for needed in choice.inputs]
    return ", ".join(relabel + [f"add {' '.join(flags + inputs)}"] * bool(flags or inputs))


def _flag(name: str, value) -> str:
    flag = "--" + name.replace("_", "-")
    return flag if value is True else f"{flag} '{value}'"
