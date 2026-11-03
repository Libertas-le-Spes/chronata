from datetime import timedelta

from chronata.timekeeping.compensation.compensation import all_labels
from chronata.timekeeping.compensation.period import Period
from chronata.timekeeping.compensation.reconciliation import Reconciliation
from chronata.timekeeping.compensation.uncovered_lateness import UncoveredLateness
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.shifts.durations import NONE, hours


def label_compensation(label: str, reconciliation: Reconciliation) -> list[str]:
    return _periods(label, reconciliation) + _unpaid_days(reconciliation.unmatched) + _lateness(reconciliation.lateness)


def totals(compensation: dict[str, Reconciliation]) -> list[str]:
    everything = all_labels(compensation)
    lines = [
        "All labels",
        f"  Overtime worked:            {hours(everything.owed.earned):>8}",
        f"  Compensated:                {_taken_off(everything.compensated):>8}",
        f"  Lateness not covered:       {_taken_off(everything.uncovered_lateness):>8}",
        f"  Unpaid:                     {hours(everything.unpaid):>8}",
    ]
    return lines + _beyond_owed(everything)


def _beyond_owed(everything: Reconciliation) -> list[str]:
    if everything.beyond_owed <= NONE:
        return []
    return [f"  Given beyond a period's overtime, not carried to other periods: {hours(everything.beyond_owed)}"]


def _periods(label: str, reconciliation: Reconciliation) -> list[str]:
    if not reconciliation.periods and not reconciliation.unmatched:
        return []
    if not reconciliation.periods:
        return ["  Compensation recorded", f"    none yet; add it with: chronata compensation FROM TO HOURS{_label_option(label)}"]
    lines = ["  Compensation recorded"]
    for period in reconciliation.periods:
        lines.append(_period_line(period))
    return lines


def _label_option(label: str) -> str:
    if not label:
        return ""
    return f" --label {label!r}"


def _period_line(period: Period) -> str:
    return (f"    {period.start} to {period.end}: overtime worked {hours(period.owed.earned)}, paid {hours(period.paid)}, "
            f"time off {hours(period.time_off)}, unpaid {hours(period.shortfall)}{_references(period)}")


def _references(period: Period) -> str:
    if not period.references:
        return ""
    return f"  [{'; '.join(period.references)}]"


def _unpaid_days(unmatched: list[Day]) -> list[str]:
    if not unmatched:
        return []
    lines = ["  Unpaid overtime"]
    for day in unmatched:
        lines.append(f"    {day.date:%Y-%m-%d %a}: {hours(day.overtime.earned)}")
    return lines


def _lateness(lateness: list[UncoveredLateness]) -> list[str]:
    if not lateness:
        return []
    lines = ["  Lateness not covered that day, taken off what is unpaid"]
    for late in lateness:
        lines.append(f"    {late.date:%Y-%m-%d %a}: {_taken_off(late.amount)}")
    return lines


def _taken_off(span: timedelta) -> str:
    return f"-{hours(span)}"
