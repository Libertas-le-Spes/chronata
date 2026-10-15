import unittest

from datetime import timedelta

from chronata.timekeeping.labels import choose, hours_by_label, worked_by_label
from chronata.timekeeping.shifts import Shift
from tests.fakes import at

KNOWN = ["Northwind", "Acme Website"]


class ChoosingALabel(unittest.TestCase):
    def test_capitals_and_spaces_do_not_make_a_new_label(self):
        for typed in ("northwind", "  NORTHWIND ", "acme   website"):
            choice = choose(typed, KNOWN)
            self.assertTrue(choice.exists, typed)
        self.assertEqual(choose("acme   website", KNOWN).label, "Acme Website")

    def test_a_near_miss_is_flagged(self):
        choice = choose("Northwnid", KNOWN)
        self.assertEqual((choice.exists, choice.near_misses), (False, ("Northwind",)))

    def test_a_genuinely_new_label_is_new_without_fuss(self):
        self.assertEqual(choose("Globex", KNOWN).near_misses, ())
        self.assertFalse(choose("Globex", KNOWN).exists)


class HoursPerLabel(unittest.TestCase):
    def test_an_open_shift_counts_up_to_now_and_is_marked_open(self):
        shifts = [Shift(1, at("2026-10-13T08:00:00"), at("2026-10-13T12:00:00"), timedelta(), "Northwind"),
                  Shift(2, at("2026-10-14T08:00:00"), None, timedelta(), "Northwind")]
        row = hours_by_label(shifts, at("2026-10-14T10:30:00"))[0]
        self.assertEqual((row.label, row.all_time, row.open_now), ("Northwind", timedelta(hours=6, minutes=30), True))


class TimePerLabel(unittest.TestCase):
    def test_hours_are_totalled_per_label(self):
        def shift(day: str, start: str, end: str, label: str) -> Shift:
            return Shift(1, at(f"{day}T{start}"), at(f"{day}T{end}"), timedelta(), label)
        totals = worked_by_label([shift("2026-10-05", "08:00", "12:00", "Acme"), shift("2026-10-05", "13:00", "15:00", "Globex"),
                                  shift("2026-10-06", "08:00", "09:00", "Acme")])
        self.assertEqual(totals, {"Acme": timedelta(hours=5), "Globex": timedelta(hours=2)})


if __name__ == "__main__":
    unittest.main()
