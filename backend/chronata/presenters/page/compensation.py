from chronata.presenters.page.facts import PageFacts
from chronata.timekeeping.compensation.compensation import Reconciliation, all_labels
from chronata.timekeeping.shifts.durations import minutes


def state(facts: PageFacts) -> dict:
    per_label = facts.compensation
    return {
        "compensation": [
            {"label": label, **_reconciliation(reconciliation)}
            for label, reconciliation in per_label.items() if reconciliation.periods or reconciliation.unmatched
        ],
        "totals": _totals(all_labels(per_label)),
    }


def _reconciliation(reconciliation: Reconciliation) -> dict:
    return {
        "periods": [
            {"start": period.start.isoformat(), "end": period.end.isoformat(), "owed": minutes(period.owed),
             "paid": minutes(period.paid), "timeOff": minutes(period.time_off), "shortfall": minutes(period.shortfall),
             "references": list(period.references)}
            for period in reversed(reconciliation.periods)
        ],
        "unmatched": [{"date": day.date.isoformat(), "overtime": minutes(day.overtime)} for day in reconciliation.unmatched],
        "totals": _totals(reconciliation),
    }


def _totals(reconciliation: Reconciliation) -> dict:
    return {
        "owed": minutes(reconciliation.owed),
        "compensated": minutes(reconciliation.compensated),
        "shortfall": minutes(reconciliation.shortfall),
        "unmatched": minutes(reconciliation.unmatched_overtime),
    }
