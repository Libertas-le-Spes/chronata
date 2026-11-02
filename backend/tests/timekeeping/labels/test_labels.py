import unittest

from datetime import timedelta

from chronata.timekeeping.labels.labels import choose
from chronata.timekeeping.labels.time_on_label import hours_by_label
from chronata.timekeeping.shifts.shifts import Shift
from tests.fakes import at

KNOWN = ["Primary", "Secondary Website"]


class ChoosingALabel(unittest.TestCase):
    def test_capitals_and_spaces_do_not_make_a_new_label(self):
        for typed in ("primary", "  PRIMARY ", "secondary   website"):
            choice = choose(typed, KNOWN)
            self.assertTrue(choice.exists, typed)
        self.assertEqual(choose("secondary   website", KNOWN).label, "Secondary Website")

    def test_a_near_miss_is_flagged(self):
        choice = choose("Primray", KNOWN)
        self.assertEqual((choice.exists, choice.near_misses), (False, ("Primary",)))

    def test_a_genuinely_new_label_is_new_without_fuss(self):
        self.assertEqual(choose("Tertiary", KNOWN).near_misses, ())
        self.assertFalse(choose("Tertiary", KNOWN).exists)


class HoursPerLabel(unittest.TestCase):
    def test_an_open_shift_counts_up_to_now_and_is_marked_open(self):
        shifts = [Shift(1, at("2026-10-13T08:00:00"), at("2026-10-13T12:00:00"), timedelta(), "Primary"),
                  Shift(2, at("2026-10-14T08:00:00"), None, timedelta(), "Primary")]
        row = hours_by_label(shifts, at("2026-10-14T10:30:00"))[0]
        self.assertEqual((row.label, row.all_time, row.open_now), ("Primary", timedelta(hours=6, minutes=30), True))


if __name__ == "__main__":
    unittest.main()
