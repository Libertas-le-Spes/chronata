from chronata.entrypoints.web.page_state.snapshot import Snapshot
from chronata.presenters.readable_copy import label_folder
from chronata.timekeeping.durations import minutes
from chronata.timekeeping.labels import hours_by_label, known_labels


def state(app, taken: Snapshot) -> dict:
    return {
        "labels": known_labels(taken.shifts),
        "defaultLabel": taken.working_day.default_label,
        "suggestedLabel": app.labels.suggested(),
        "labelSummary": [
            {"label": row.label, "folder": label_folder(row.label), "week": minutes(row.this_week), "all": minutes(row.all_time), "openNow": row.open_now}
            for row in hours_by_label(taken.shifts, taken.now)
        ],
    }
