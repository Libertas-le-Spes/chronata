from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Break:
    start: datetime
    end: datetime
    cause: str
    reason: str = ""


@dataclass
class Shift:
    id: int
    start: datetime
    end: datetime | None
    entered_late_by: timedelta
    label: str = ""
    breaks: list[Break] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)
    voided: bool = False

    @property
    def since(self) -> datetime:
        return self.breaks[-1].end if self.breaks else self.start

    def worked(self, until: datetime) -> timedelta:
        return sum((ends - begins for begins, ends in self.segments(until)), timedelta())

    def segments(self, until: datetime) -> list[tuple[datetime, datetime]]:
        finish = self.end or until
        pieces, cursor = [], self.start
        for gap in self.breaks:
            pieces.append((cursor, gap.start))
            cursor = gap.end
        pieces.append((cursor, finish))
        return [(begins, ends) for begins, ends in pieces if ends > begins]


def open_shift(all_shifts: list[Shift]) -> Shift | None:
    return next((shift for shift in all_shifts if shift.end is None and not shift.voided), None)


def completed(all_shifts: list[Shift]) -> list[Shift]:
    return [shift for shift in all_shifts if shift.end is not None and not shift.voided]
