from dataclasses import dataclass
from datetime import date, timedelta

from chronata.timekeeping.compensation.given import Given
from chronata.timekeeping.hours.overtime import Overtime
from chronata.timekeeping.shifts.durations import NONE


@dataclass(frozen=True)
class Period:
    start: date
    end: date
    owed: Overtime
    given: tuple[Given, ...]

    @property
    def paid(self) -> timedelta:
        return sum((each.paid for each in self.given), NONE)

    @property
    def time_off(self) -> timedelta:
        return sum((each.time_off for each in self.given), NONE)

    @property
    def references(self) -> tuple[str, ...]:
        found = []
        for each in self.given:
            if each.reference:
                found.append(each.reference)
        return tuple(found)

    @property
    def given_in_all(self) -> timedelta:
        return self.paid + self.time_off

    @property
    def shortfall(self) -> timedelta:
        return max(self.owed.earned - self.given_in_all, NONE)

    @property
    def counted_against_owed(self) -> timedelta:
        return min(self.given_in_all, self.owed.earned)

    @property
    def beyond_owed(self) -> timedelta:
        return max(self.given_in_all - self.owed.earned, NONE)

    def covers(self, day: date) -> bool:
        return self.start <= day <= self.end
