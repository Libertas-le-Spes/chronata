from chronata.presenters.page import chart, clock, compensation, hours, labels, safekeeping, shifts
from chronata.presenters.page.facts import PageFacts

SECTIONS = [clock, shifts, labels, chart, compensation, safekeeping, hours]


def page_state(facts: PageFacts) -> dict:
    return {key: value for section in SECTIONS for key, value in section.state(facts).items()}
