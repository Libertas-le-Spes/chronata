from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from chronata.timekeeping.compensation.given import Given
from chronata.timekeeping.entries.compensation import Compensated
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.overtime import NONE, Overtime, total
from chronata.timekeeping.hours.week import Week
from chronata.timekeeping.record.record import Entry


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
    def shortfall(self) -> timedelta:
        return max(self.owed.earned - self.paid - self.time_off, NONE)

    def covers(self, day: date) -> bool:
        return self.start <= day <= self.end


@dataclass(frozen=True)
class Reconciliation:
    periods: list[Period]
    unmatched: list[Day]

    @property
    def owed(self) -> Overtime:
        return total(period.owed for period in self.periods) + self.unmatched_overtime

    @property
    def compensated(self) -> timedelta:
        return sum((period.paid + period.time_off for period in self.periods), NONE)

    @property
    def shortfall(self) -> timedelta:
        return sum((period.shortfall for period in self.periods), NONE)

    @property
    def unmatched_overtime(self) -> Overtime:
        return total(day.overtime for day in self.unmatched)


def reconcile_by_label(entries: list[Entry], weeks_per_label: dict[str, list[Week]], default_label: str) -> dict[str, Reconciliation]:
    records: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        if entry.kind == Compensated.kind:
            records[_label_of(entry, default_label)].append(entry)
    by_label = {}
    for label in _default_first(set(weeks_per_label) | set(records), default_label):
        by_label[label] = reconcile(records[label], weeks_per_label.get(label, []))
    return by_label


def all_labels(by_label: dict[str, Reconciliation]) -> Reconciliation:
    periods, unmatched = [], []
    for reconciliation in by_label.values():
        periods += reconciliation.periods
        unmatched += reconciliation.unmatched
    return Reconciliation(periods, unmatched)


def reconcile(entries: list[Entry], all_weeks: list[Week]) -> Reconciliation:
    days = _days_with_overtime(all_weeks)
    grouped: dict[tuple[date, date], list[Given]] = defaultdict(list)
    for entry in entries:
        if entry.kind == Compensated.kind:
            record = Compensated.of(entry)
            grouped[(record.start, record.end)].append(record.given)
    periods = [_period(start, end, grouped[(start, end)], days) for start, end in sorted(grouped)]
    return Reconciliation(periods, _not_covered(days, periods))


def _days_with_overtime(all_weeks: list[Week]) -> list[Day]:
    found = []
    for week in all_weeks:
        for day in week.days:
            if day.overtime.earned_some:
                found.append(day)
    return found


def _period(start: date, end: date, given: list[Given], days: list[Day]) -> Period:
    owed = []
    for day in days:
        if start <= day.date <= end:
            owed.append(day.overtime)
    return Period(start, end, total(owed), tuple(given))


def _not_covered(days: list[Day], periods: list[Period]) -> list[Day]:
    uncovered = []
    for day in days:
        if not _covered_by_any(day, periods):
            uncovered.append(day)
    return uncovered


def _covered_by_any(day: Day, periods: list[Period]) -> bool:
    for period in periods:
        if period.covers(day.date):
            return True
    return False


def _label_of(entry: Entry, default_label: str) -> str:
    label = entry.data.get("label", "")
    if label:
        return label
    return default_label


def _default_first(labels: set[str], default_label: str) -> list[str]:
    others = sorted(labels - {default_label}, key=str.casefold)
    if default_label in labels:
        return [default_label, *others]
    return others
