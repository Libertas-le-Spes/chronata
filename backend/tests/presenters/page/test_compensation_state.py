import unittest
from datetime import date, timedelta
from types import SimpleNamespace

from chronata.presenters.page.compensation import state
from chronata.timekeeping.compensation.lateness_offset import LatenessOffset
from chronata.timekeeping.compensation.reconciliation import Reconciliation

ONLY_LATENESS = Reconciliation([], [], [LatenessOffset(date(2026, 10, 6), timedelta(minutes=7))])


class LatenessOnThePage(unittest.TestCase):
    def setUp(self):
        self.shown = state(SimpleNamespace(compensation={"Northwind": ONLY_LATENESS}))

    def test_a_label_with_only_lateness_still_gets_a_section_listing_it(self):
        self.assertEqual(self.shown["compensation"][0]["lateness"], [{"date": "2026-10-06", "late": 7}])

    def test_the_totals_carry_the_lateness_and_what_is_left(self):
        totals = self.shown["totals"]
        self.assertEqual((totals["latenessOffset"], totals["uncompensated"]), (7, -7))


if __name__ == "__main__":
    unittest.main()
