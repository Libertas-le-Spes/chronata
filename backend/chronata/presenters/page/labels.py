from chronata.presenters.page.facts import PageFacts
from chronata.presenters.readable_copy.readable_copy import label_folder
from chronata.timekeeping.labels.labels import hours_by_label, known_labels
from chronata.timekeeping.shifts.durations import minutes


def state(facts: PageFacts) -> dict:
    worked = hours_by_label(facts.shifts, facts.now)
    unused = [label for label in facts.hours.labels() if label not in {row.label for row in worked}]
    return {
        "labels": known_labels(facts.shifts) + unused,
        "defaultLabel": facts.hours.default_label,
        "suggestedLabel": facts.suggested_label,
        "labelSummary": [
            {"label": row.label, "folder": label_folder(row.label), "week": minutes(row.this_week), "all": minutes(row.all_time), "openNow": row.open_now}
            for row in worked
        ] + [{"label": label, "folder": label_folder(label), "week": 0, "all": 0, "openNow": False} for label in unused],
    }
