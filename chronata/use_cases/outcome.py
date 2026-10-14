from dataclasses import dataclass


class UserError(Exception):
    pass


class UnconfirmedLabel(UserError):
    def __init__(self, label: str, near_misses: tuple[str, ...]):
        self.label = label
        self.near_misses = near_misses
        options = " or ".join(near_misses)
        super().__init__(f"'{label}' would start a new label and folder. Did you mean {options}? Use that, or confirm '{label}' as new.")


@dataclass(frozen=True)
class Outcome:
    message: str
    warning: str | None
