import unittest

from chronata.timekeeping.labels import choose

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


if __name__ == "__main__":
    unittest.main()
