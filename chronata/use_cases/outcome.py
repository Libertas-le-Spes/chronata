from dataclasses import dataclass


class UserError(Exception):
    pass


class UnconfirmedLabel(UserError):
    def __init__(self, label: str, near_misses: tuple[str, ...]):
        self.label = label
        self.near_misses = near_misses
        options = " or ".join(near_misses)
        super().__init__(f"'{label}' would start a new label and folder. Did you mean {options}? Use that, or confirm '{label}' as new.")


class OffDefaultLabel(UserError):
    def __init__(self, label: str, default_label: str):
        self.label = label
        self.default_label = default_label
        chosen = f"on {label}" if label else "with no label"
        super().__init__(f"it's a workday and your default is {default_label}. Clock in {chosen} instead?")


@dataclass(frozen=True)
class Outcome:
    message: str
    warning: str | None
