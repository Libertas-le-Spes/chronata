from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from chronata.timekeeping.entries.compensation import PAID, TIME_OFF, Compensated
from chronata.timekeeping.record import Entry
from chronata.timekeeping.overtime import NONE, Day, Week


@dataclass(frozen=True)
class Period:
    start: date
    end: date
    owed: timedelta
    paid: timedelta
    time_off: timedelta
    references: tuple[str, ...]

    @property
    def shortfall(self) -> timedelta:
        return max(self.owed - self.paid - self.time_off, NONE)


@dataclass(frozen=True)
class Reconciliation:
    periods: list[Period]
    unmatched: list[Day]

    @property
    def owed(self) -> timedelta:
        return sum((period.owed for period in self.periods), NONE) + self.unmatched_overtime

    @property
    def compensated(self) -> timedelta:
        return sum((period.paid + period.time_off for period in self.periods), NONE)

    @property
    def shortfall(self) -> timedelta:
        return sum((period.shortfall for period in self.periods), NONE)

    @property
    def unmatched_overtime(self) -> timedelta:
        return sum((day.overtime for day in self.unmatched), NONE)


def reconcile_by_label(entries: list[Entry], weeks_per_label: dict[str, list[Week]], default_label: str) -> dict[str, Reconciliation]:
    records: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        if entry.kind == Compensated.kind:
            records[entry.data.get("label") or default_label].append(entry)
    labels = sorted(set(weeks_per_label) | set(records), key=lambda label: (label != default_label, label.casefold()))
    return {label: reconcile(records[label], weeks_per_label.get(label, [])) for label in labels}


def all_labels(by_label: dict[str, Reconciliation]) -> Reconciliation:
    return Reconciliation([p for r in by_label.values() for p in r.periods], [d for r in by_label.values() for d in r.unmatched])


def reconcile(entries: list[Entry], all_weeks: list[Week]) -> Reconciliation:
    days = [day for week in all_weeks for day in week.days if day.overtime > NONE]
    grouped: dict[tuple[date, date], list[dict]] = defaultdict(list)
    for entry in entries:
        if entry.kind == Compensated.kind:
            grouped[(date.fromisoformat(entry.data["from"]), date.fromisoformat(entry.data["to"]))].append(entry.data)
    periods = [_period(start, end, records, days) for (start, end), records in sorted(grouped.items())]
    unmatched = [day for day in days if not any(period.start <= day.date <= period.end for period in periods)]
    return Reconciliation(periods, unmatched)


def _period(start: date, end: date, records: list[dict], days: list[Day]) -> Period:
    return Period(
        start,
        end,
        sum((day.overtime for day in days if start <= day.date <= end), NONE),
        sum((timedelta(hours=r["hours"]) for r in records if r["kind"] == PAID), NONE),
        sum((timedelta(hours=r["hours"]) for r in records if r["kind"] == TIME_OFF), NONE),
        tuple(r["reference"] for r in records if r.get("reference")),
    )
