from dataclasses import dataclass, field, fields

from chronata.use_cases.outcome import UserError


@dataclass(frozen=True)
class Answers:
    new_label: bool = False
    off_default: bool = False
    shift: str = ""
    lunch: str = ""
    no_set_hours: bool = False

    @classmethod
    def from_dict(cls, given: dict) -> "Answers":
        return cls(**{answer.name: given[answer.name] for answer in fields(cls) if answer.name in given})

    @property
    def gave_hours(self) -> bool:
        return self.no_set_hours or bool(self.shift.strip())


@dataclass(frozen=True)
class Input:
    name: str
    prompt: str
    example: str


@dataclass(frozen=True)
class Choice:
    caption: str
    label: str | None = None
    answers: dict = field(default_factory=dict)
    inputs: tuple[Input, ...] = ()


class Question(UserError):
    def __init__(self, text: str, choices: list[Choice]):
        super().__init__(text)
        self.text = text
        self.choices = choices


class UnconfirmedLabel(Question):
    def __init__(self, label: str, near_misses: tuple[str, ...]):
        self.label = label
        self.near_misses = near_misses
        options = " or ".join(f"“{miss}”" for miss in near_misses)
        super().__init__(f"“{label}” would start a new label, with its own folder. Did you mean {options}?",
                         [*(Choice(f"Use “{miss}”", label=miss) for miss in near_misses), Choice(f"Create “{label}”", answers={"new_label": True})])


class LabelNeedsHours(Question):
    def __init__(self, label: str):
        self.label = label
        hours = (Input("shift", "When does its shift start and end?", "08:00 to 17:00"),
                 Input("lunch", "Lunch, if there is one (leave it empty for none)", "12:00 for 30 min"))
        super().__init__(f"“{label}” is a new label, with its own folder. What are its hours? "
                         "They are remembered, so next time clocking in on it just starts.",
                         [Choice("Save its hours", answers={"new_label": True}, inputs=hours),
                          Choice("No set hours", answers={"new_label": True, "no_set_hours": True})])


class OffDefaultLabel(Question):
    def __init__(self, label: str, default_label: str):
        self.label = label
        self.default_label = default_label
        chosen = f"Clock in on “{label}”" if label else "Clock in with no label"
        super().__init__(f"Today is a workday, and “{default_label}” is your default. {chosen} instead?",
                         [Choice(f"Use “{default_label}”", label=default_label), Choice(chosen, answers={"off_default": True})])
