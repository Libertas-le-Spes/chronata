import unittest
from datetime import date, timedelta
from unittest.mock import create_autospec

from chronata.presenters.page.compensation import state
from chronata.presenters.page.facts import PageFacts
from chronata.timekeeping.compensation.uncovered_lateness import UncoveredLateness
from chronata.timekeeping.compensation.reconciliation import Reconciliation

ONLY_LATENESS = Reconciliation([], [], [UncoveredLateness(date(2026, 10, 6), timedelta(minutes=7))])


class LatenessOnThePage(unittest.TestCase):
    def setUp(self):
        facts = create_autospec(PageFacts, instance=True)
        facts.compensation = {"Primary": ONLY_LATENESS}
        self.shown = state(facts)

    def test_a_label_with_only_lateness_still_gets_a_section_listing_it(self):
        self.assertEqual(self.shown["compensation"][0]["lateness"], [{"date": "2026-10-06", "late": 7}])

    def test_the_unpaid_total_has_the_lateness_taken_off(self):
        totals = self.shown["totals"]
        self.assertEqual(totals["unpaid"], -7)


if __name__ == "__main__":
    unittest.main()
