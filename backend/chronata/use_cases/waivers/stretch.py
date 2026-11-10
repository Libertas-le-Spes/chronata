from dataclasses import dataclass
from datetime import datetime, timedelta

from chronata.timekeeping.shifts.durations import NONE
from chronata.timekeeping.shifts.shifts import WAIVED, Break, Shift


@dataclass(frozen=True)
class Stretch:
    shift: Shift
    begins: datetime
    ends: datetime

    @property
    def length(self) -> timedelta:
        return self.ends - self.begins

    def waived(self, reason: str) -> Break:
        return Break(self.begins, self.ends, WAIVED, reason)

    def from_moment(self, moment: datetime) -> "Stretch":
        return Stretch(self.shift, max(self.begins, moment), self.ends)

    def first(self, length: timedelta) -> "Stretch":
        return Stretch(self.shift, self.begins, min(self.begins + length, self.ends))

    def without(self, part: "Stretch") -> list["Stretch"]:
        pieces = []
        for piece in (Stretch(self.shift, self.begins, part.begins), Stretch(self.shift, part.ends, self.ends)):
            if piece.length > NONE:
                pieces.append(piece)
        return pieces
