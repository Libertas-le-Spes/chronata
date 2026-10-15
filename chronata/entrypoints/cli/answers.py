from chronata.use_cases.questions import Answers, Choice, Question


def hours_options(command) -> None:
    command.add_argument("--shift", help="when the shift starts and ends, e.g. '08:00 to 17:00'")
    command.add_argument("--lunch", help="when lunch is and how long, e.g. '12:00 for 30 min'; leave out for no lunch")
    command.add_argument("--no-set-hours", action="store_true", help="no shift times: only the time worked is counted")


def answer_options(command) -> None:
    hours_options(command)
    command.add_argument("--new-label", action="store_true", help="confirm a new label that looks like an existing one")
    command.add_argument("--off-default", action="store_true", help="confirm working on a label other than the default on a workday")


def answers(args) -> Answers:
    return Answers(args.new_label, args.off_default, args.shift or "", args.lunch or "", args.no_set_hours)


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
