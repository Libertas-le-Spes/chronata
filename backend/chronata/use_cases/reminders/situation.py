from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.shifts.shifts import Shift


@dataclass(frozen=True)
class Nudge:
    summary: str
    body: str
    on_click: Callable[[], None] | None = None
    click_label: str = "Open"


class Actions:
    def __init__(self, clock_in: Callable[[str], None], clock_out: Callable[[str | None, str], None], open_page: Callable[[str], None]):
        self._clock_in = clock_in
        self._clock_out = clock_out
        self._open_page = open_page

    def clock_in(self, note: str) -> Callable[[], None]:
        return lambda: self._clock_in(note)

    def clock_out(self, at: str | None, note: str) -> Callable[[], None]:
        return lambda: self._clock_out(at, note)

    def open(self, section: str = "") -> Callable[[], None]:
        return lambda: self._open_page(section)


@dataclass(frozen=True)
class Situation:
    now: datetime
    current: Shift | None
    finished_today: list[Shift]
    hours: LabelHours
    actions: Actions

    def lunch_of(self, label: str) -> tuple[datetime, datetime] | None:
        working_day = self.hours.for_label(label)
        return working_day.lunch_on(self.now.date(), self.now.tzinfo) if working_day else None
