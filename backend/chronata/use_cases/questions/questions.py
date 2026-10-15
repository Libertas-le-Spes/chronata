from dataclasses import dataclass, field, fields, replace

from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.use_cases.log.outcome import UserError


@dataclass(frozen=True)
class Answers:
    new_label: bool = False
    off_default: bool = False
    shift_start: str = ""
    shift_end: str = ""
    lunch_start: str = ""
    lunch_minutes: str = ""
    no_set_hours: bool = False

    @classmethod
    def from_dict(cls, given: dict) -> "Answers":
        return cls(**{answer.name: given[answer.name] for answer in fields(cls) if answer.name in given})

    @property
    def gave_hours(self) -> bool:
        return self.no_set_hours or bool(self.shift_start.strip())


@dataclass(frozen=True)
class Input:
    name: str
    prompt: str
    example: str
    type: str = "text"
    required: bool = False
    opts_out: bool = False
    value: str = ""


HOURS_INPUTS = (
    Input("shift_start", "Shift starts at", "830", "time", required=True),
    Input("shift_end", "Shift ends at", "1730", "time", required=True),
    Input("lunch_start", "Lunch starts at (leave empty for no lunch)", "1200", "time", opts_out=True),
    Input("lunch_minutes", "Lunch in minutes (leave empty for no lunch)", "45", "number", opts_out=True),
)


def hours_values(day: WorkingDay | None) -> dict[str, str]:
    if day is None:
        return {}
    lunch = {"lunch_start": f"{day.lunch.start:%H:%M}", "lunch_minutes": str(day.lunch.minutes)} if day.lunch else {}
    return {"shift_start": f"{day.shift_start:%H:%M}", "shift_end": f"{day.shift_end:%H:%M}", **lunch}


def filled_in(inputs: tuple[Input, ...], values: dict[str, str]) -> tuple[Input, ...]:
    return tuple(replace(needed, value=values.get(needed.name, needed.value)) for needed in inputs)


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
        super().__init__(f"“{label}” is a new label, with its own folder. What are its hours? "
                         "They are remembered, so next time clocking in on it just starts.",
                         [Choice("Save its hours", answers={"new_label": True}, inputs=HOURS_INPUTS),
                          Choice("No set hours", answers={"new_label": True, "no_set_hours": True})])


class OffDefaultLabel(Question):
    def __init__(self, label: str, default_label: str):
        self.label = label
        self.default_label = default_label
        chosen = f"Clock in on “{label}”" if label else "Clock in with no label"
        super().__init__(f"Today is a workday, and “{default_label}” is your default. {chosen} instead?",
                         [Choice(f"Use “{default_label}”", label=default_label), Choice(chosen, answers={"off_default": True})])
