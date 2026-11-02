from collections import defaultdict
from datetime import date

from chronata.timekeeping.compensation.given import Given
from chronata.timekeeping.compensation.lateness_offset import lateness_offsets
from chronata.timekeeping.compensation.period import Period
from chronata.timekeeping.compensation.reconciliation import Reconciliation
from chronata.timekeeping.entries.compensation import Compensated
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.overtime import total
from chronata.timekeeping.hours.week import Week
from chronata.timekeeping.record.record import Entry


def reconcile_by_label(entries: list[Entry], weeks_per_label: dict[str, list[Week]], hours: LabelHours) -> dict[str, Reconciliation]:
    records: dict[str, list[Compensated]] = defaultdict(list)
    for record in compensations(entries):
        records[hours.counted_under(record.label)].append(record)
    by_label = {}
    for label in _default_first(set(weeks_per_label) | set(records), hours.default_label):
        by_label[label] = reconcile(records[label], weeks_per_label.get(label, []))
    return by_label


def all_labels(by_label: dict[str, Reconciliation]) -> Reconciliation:
    periods, unmatched, lateness = [], [], []
    for reconciliation in by_label.values():
        periods += reconciliation.periods
        unmatched += reconciliation.unmatched
        lateness += reconciliation.lateness
    return Reconciliation(periods, unmatched, lateness)


def compensations(entries: list[Entry]) -> list[Compensated]:
    found = []
    for entry in entries:
        if entry.kind == Compensated.kind:
            found.append(Compensated.of(entry))
    return found


def reconcile(records: list[Compensated], all_weeks: list[Week]) -> Reconciliation:
    days = _days_with_overtime(all_weeks)
    grouped: dict[tuple[date, date], list[Given]] = defaultdict(list)
    for record in records:
        grouped[(record.start, record.end)].append(record.given)
    periods = [_period(start, end, grouped[(start, end)], days) for start, end in sorted(grouped)]
    return Reconciliation(periods, _not_covered(days, periods), lateness_offsets(all_weeks))


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


def _default_first(labels: set[str], default_label: str) -> list[str]:
    others = sorted(labels - {default_label}, key=_alphabetical)
    if default_label in labels:
        return [default_label] + others
    return others


def _alphabetical(label: str) -> tuple[str, str]:
    return label.casefold(), label
