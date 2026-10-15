from dataclasses import dataclass


class UserError(Exception):
    pass


@dataclass(frozen=True)
class Outcome:
    message: str
    warning: str | None
