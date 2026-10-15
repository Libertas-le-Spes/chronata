from chronata.entrypoints.web.page_state import chart, clock, compensation, hours, labels, safekeeping, shifts
from chronata.entrypoints.web.page_state.snapshot import Snapshot

SECTIONS = [clock, shifts, labels, chart, compensation, safekeeping, hours]


def page_state(app) -> dict:
    taken = Snapshot.of(app)
    return {key: value for section in SECTIONS for key, value in section.state(app, taken).items()}
