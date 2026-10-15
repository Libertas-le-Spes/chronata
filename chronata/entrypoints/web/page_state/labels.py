from chronata.entrypoints.web.page_state.snapshot import Snapshot
from chronata.presenters.readable_copy import label_folder
from chronata.timekeeping.durations import minutes
from chronata.timekeeping.labels import hours_by_label, known_labels


def state(app, taken: Snapshot) -> dict:
    worked = hours_by_label(taken.shifts, taken.now)
    unused = [label for label in taken.hours.labels() if label not in {row.label for row in worked}]
    return {
        "labels": known_labels(taken.shifts) + unused,
        "defaultLabel": taken.hours.default_label,
        "suggestedLabel": app.labels.suggested(),
        "labelSummary": [
            {"label": row.label, "folder": label_folder(row.label), "week": minutes(row.this_week), "all": minutes(row.all_time), "openNow": row.open_now}
            for row in worked
        ] + [{"label": label, "folder": label_folder(label), "week": 0, "all": 0, "openNow": False} for label in unused],
    }
