from chronata.entrypoints.web.page_state.snapshot import Snapshot
from chronata.timekeeping.durations import minutes


def state(app, taken: Snapshot) -> dict:
    reconciliation = app.log.reconciliation(app.log.main_weeks())
    return {
        "periods": [
            {"start": period.start.isoformat(), "end": period.end.isoformat(), "owed": minutes(period.owed),
             "paid": minutes(period.paid), "timeOff": minutes(period.time_off), "shortfall": minutes(period.shortfall),
             "references": list(period.references)}
            for period in reversed(reconciliation.periods)
        ],
        "unmatched": [{"date": day.date.isoformat(), "overtime": minutes(day.overtime)} for day in reconciliation.unmatched],
        "totals": {
            "owed": minutes(reconciliation.owed),
            "compensated": minutes(reconciliation.compensated),
            "shortfall": minutes(reconciliation.shortfall),
            "unmatched": minutes(reconciliation.unmatched_overtime),
        },
    }
