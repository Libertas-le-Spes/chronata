from chronata.presenters.page.facts import PageFacts
from chronata.timekeeping.compensation.compensation import all_labels
from chronata.timekeeping.compensation.period import Period
from chronata.timekeeping.compensation.reconciliation import Reconciliation
from chronata.timekeeping.hours.day import Day
from chronata.timekeeping.shifts.durations import minutes


def state(facts: PageFacts) -> dict:
    per_label = facts.compensation
    shown = []
    for label, reconciliation in per_label.items():
        if reconciliation.periods or reconciliation.unmatched:
            shown.append(_labelled(label, reconciliation))
    return {"compensation": shown, "totals": _totals(all_labels(per_label))}


def _labelled(label: str, reconciliation: Reconciliation) -> dict:
    return {
        "label": label,
        "periods": [_period(period) for period in reversed(reconciliation.periods)],
        "unmatched": [_unmatched(day) for day in reconciliation.unmatched],
        "totals": _totals(reconciliation),
    }


def _period(period: Period) -> dict:
    return {"start": period.start.isoformat(), "end": period.end.isoformat(), "owed": minutes(period.owed.earned),
            "paid": minutes(period.paid), "timeOff": minutes(period.time_off), "shortfall": minutes(period.shortfall),
            "references": list(period.references)}


def _unmatched(day: Day) -> dict:
    return {"date": day.date.isoformat(), "overtime": minutes(day.overtime.earned)}


def _totals(reconciliation: Reconciliation) -> dict:
    return {
        "owed": minutes(reconciliation.owed.earned),
        "compensated": minutes(reconciliation.compensated),
        "shortfall": minutes(reconciliation.shortfall),
        "unmatched": minutes(reconciliation.unmatched_overtime.earned),
    }
