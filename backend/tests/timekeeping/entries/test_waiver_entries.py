import unittest

from chronata.timekeeping.entries.clocking import ClockIn, ClockOut
from chronata.timekeeping.entries.corrections import BreakExplained
from chronata.timekeeping.entries.waivers import TimeWaived, WaiverWithdrawn
from chronata.timekeeping.record.record import Entry
from chronata.timekeeping.shifts.replay import shifts
from tests.fakes import at

SIX = at("2026-10-15T18:00:00")
NINE = at("2026-10-15T21:00:00")


class WhatAWaiverRecords(unittest.TestCase):
    def test_a_waived_stretch_records_its_shift_times_and_reason(self):
        self.assertEqual(TimeWaived(66, SIX, NINE, "forgot to clock out").data(),
                         {"shift": 66, "start": SIX.isoformat(), "end": NINE.isoformat(), "reason": "forgot to clock out"})

    def test_counting_it_again_records_which_waiver_and_why(self):
        self.assertEqual(WaiverWithdrawn(66, SIX, "was working").data(), {"shift": 66, "start": SIX.isoformat(), "reason": "was working"})



def written(seq: int, entry) -> Entry:
    return Entry(seq, entry.kind, NINE, entry.data())


def evening_with(*later) -> list[Entry]:
    entries = [written(1, ClockIn(at("2026-10-15T08:00:00"), "boot")), written(2, ClockOut(1, NINE, "boot"))]
    for seq, entry in enumerate(later, start=3):
        entries.append(written(seq, entry))
    return entries


class ReplayingWaivers(unittest.TestCase):
    def test_a_waiver_ending_before_it_starts_is_not_applied(self):
        replayed = shifts(evening_with(TimeWaived(1, NINE, SIX, "backwards")))[0]
        self.assertEqual(replayed.breaks, [])

    def test_explaining_a_waiver_as_a_pc_break_changes_nothing(self):
        replayed = shifts(evening_with(TimeWaived(1, SIX, NINE, "forgot"), BreakExplained(1, SIX.isoformat(), "power cut")))[0]
        self.assertEqual((replayed.breaks[0].reason, replayed.happenings[-1].what), ("forgot", "Waived"))


if __name__ == "__main__":
    unittest.main()
