from chronata.entrypoints.web.page_state import chart, clock, labels, pay, safekeeping, shifts, working_day
from chronata.entrypoints.web.page_state.snapshot import Snapshot

SECTIONS = [clock, shifts, labels, chart, pay, safekeeping, working_day]


def page_state(app) -> dict:
    taken = Snapshot.of(app)
    return {key: value for section in SECTIONS for key, value in section.state(app, taken).items()}
