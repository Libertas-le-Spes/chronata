import unittest
from datetime import timedelta
from unittest.mock import create_autospec

from chronata.presenters.page.facts import PageFacts
from chronata.presenters.page.shifts import state
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.shifts.shifts import CLOCKED_OUT, WAIVED, Break, Happening, Shift
from tests.fakes import at


def clocked_day(voided: bool = False) -> Shift:
    start = at("2026-10-14T08:00:00")
    return Shift(4, start, at("2026-10-14T23:00:00"), timedelta(), voided=voided, happenings=[Happening(start, "Manual clock in")])


def facts_for(shift: Shift) -> PageFacts:
    facts = create_autospec(PageFacts, instance=True)
    facts.shifts, facts.weeks, facts.sessions, facts.stamps = [shift], [], [], []
    facts.hours, facts.now = LabelHours(), at("2026-10-15T09:00:00")
    return facts


class WaiversOnThePage(unittest.TestCase):
    def test_a_day_lists_its_waived_stretches_and_not_its_other_breaks(self):
        shift = clocked_day()
        shift.add_break(Break(at("2026-10-14T12:00:00"), at("2026-10-14T13:00:00"), CLOCKED_OUT))
        shift.add_break(Break(at("2026-10-14T18:00:00"), at("2026-10-14T23:00:00"), WAIVED, "forgot to clock out"))
        waivers = state(facts_for(shift))["entries"][0]["waivers"]
        self.assertEqual(waivers, [{"shift": 4, "start": at("2026-10-14T18:00:00").isoformat(), "end": at("2026-10-14T23:00:00").isoformat(),
                                    "minutes": 300, "reason": "forgot to clock out"}])

    def test_a_shift_marked_as_a_mistake_lists_no_waivers(self):
        shift = clocked_day(voided=True)
        shift.add_break(Break(at("2026-10-14T18:00:00"), at("2026-10-14T23:00:00"), WAIVED, "forgot to clock out"))
        self.assertEqual(state(facts_for(shift))["entries"][0]["waivers"], [])


if __name__ == "__main__":
    unittest.main()
