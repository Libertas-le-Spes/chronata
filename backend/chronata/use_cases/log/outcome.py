from dataclasses import dataclass


class UserError(Exception):
    pass


@dataclass(frozen=True)
class Outcome:
    message: str
    warning: str | None

    @property
    def headline(self) -> str:
        return self.message[:1].upper() + self.message[1:]
