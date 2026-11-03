import unittest

from chronata.timekeeping.entries.waivers import TimeWaived, WaiverWithdrawn
from tests.fakes import at

SIX = at("2026-10-15T18:00:00")
NINE = at("2026-10-15T21:00:00")


class WhatAWaiverRecords(unittest.TestCase):
    def test_a_waived_stretch_records_its_shift_times_and_reason(self):
        self.assertEqual(TimeWaived(66, SIX, NINE, "forgot to clock out").data(),
                         {"shift": 66, "start": SIX.isoformat(), "end": NINE.isoformat(), "reason": "forgot to clock out"})

    def test_counting_it_again_records_which_waiver_and_why(self):
        self.assertEqual(WaiverWithdrawn(66, SIX, "was working").data(), {"shift": 66, "start": SIX.isoformat(), "reason": "was working"})


if __name__ == "__main__":
    unittest.main()
