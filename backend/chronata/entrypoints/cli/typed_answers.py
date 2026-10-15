from typing import Callable

from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions import typed_input
from chronata.use_cases.questions.questions import Choice, Input, Question

Ask = Callable[[str], str]


class TimeAnswer:
    def read(self, text: str) -> str:
        return f"{typed_input.clock_number(text):%H:%M}"

    def shown(self, value: str) -> str:
        return value.replace(":", "")


class MinutesAnswer:
    def read(self, text: str) -> str:
        return str(typed_input.minutes_number(text))

    def shown(self, value: str) -> str:
        return value


class TextAnswer:
    def read(self, text: str) -> str:
        return text

    def shown(self, value: str) -> str:
        return value


ANSWERS_BY_TYPE = {"time": TimeAnswer(), "number": MinutesAnswer(), "text": TextAnswer()}


def ask_inputs(ask: Ask, inputs: tuple[Input, ...]) -> dict[str, str]:
    given = {}
    for needed in inputs:
        value = _asked(ask, f"{needed.prompt} {_hint(needed)}: ", lambda text, needed=needed: _value(needed, text))
        if needed.opts_out and not value:
            break
        given[needed.name] = value
    return given


def ask_choice(ask: Ask, question: Question) -> tuple[str | None, dict] | None:
    print(question.text)
    for number, choice in enumerate(question.choices, 1):
        print(f"  {number}) {choice.caption}")
    choice = _asked(ask, "Choose a number, or press Enter to cancel: ", lambda text: _choice(question.choices, text))
    if choice is None:
        return None
    return choice.label, {**choice.answers, **ask_inputs(ask, choice.inputs)}


def _hint(needed: Input) -> str:
    if not needed.value:
        return f"[e.g. {needed.example}]"
    shown = ANSWERS_BY_TYPE[needed.type].shown(needed.value)
    return f"[now {shown}]" if needed.opts_out else f"[{shown}]"


def _value(needed: Input, text: str) -> str:
    if text:
        return ANSWERS_BY_TYPE[needed.type].read(text)
    if needed.opts_out or not needed.required:
        return ""
    if needed.value:
        return needed.value
    raise UserError("this one needs an answer")


def _choice(choices: list[Choice], text: str) -> Choice | None:
    if not text:
        return None
    if text.isdigit() and 1 <= int(text) <= len(choices):
        return choices[int(text) - 1]
    raise UserError(f"type a number from 1 to {len(choices)}")


def _asked(ask: Ask, prompt: str, read: Callable):
    while True:
        try:
            return read(ask(prompt).strip())
        except UserError as error:
            print(f"  {error}")
