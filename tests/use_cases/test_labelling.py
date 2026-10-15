import unittest

from chronata.use_cases.outcome import UnconfirmedLabel
from tests.fakes import Fixture


class Labels(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T17:00:00")
        self.f.app.corrections.add("2026-10-13", "08:00", "12:00", "written later", None, "Northwind")

    def labels_of_shifts(self) -> list[str]:
        return [shift.label for shift in self.f.app.log.shifts()]

    def test_the_existing_spelling_is_used_whatever_the_capitals(self):
        self.f.app.corrections.add("2026-10-14", "08:00", "12:00", "written later", None, "northwind ")
        self.assertEqual(self.labels_of_shifts(), ["Northwind", "Northwind"])

    def test_a_near_miss_needs_confirming_before_it_becomes_a_new_label(self):
        with self.assertRaises(UnconfirmedLabel) as raised:
            self.f.app.corrections.add("2026-10-14", "08:00", "12:00", "written later", None, "Northwnid")
        self.assertEqual(raised.exception.near_misses, ("Northwind",))
        self.f.app.corrections.add("2026-10-14", "08:00", "12:00", "written later", None, "Northwnid", new_label=True)
        self.assertIn("Northwnid", self.labels_of_shifts())

    def test_renaming_moves_every_shift_and_stays_on_the_record(self):
        self.f.app.corrections.add("2026-10-14", "08:00", "12:00", "written later", None, "Northwind")
        outcome = self.f.app.labels.rename("northwind", "Northwind Ltd")
        self.assertEqual(self.labels_of_shifts(), ["Northwind Ltd", "Northwind Ltd"])
        self.assertIn("on 2 shifts", outcome.message)
        self.assertIn("label changed from Northwind to Northwind Ltd", self.f.app.log.shifts()[0].changes[-1])

    def test_renaming_onto_an_existing_label_merges_them(self):
        self.f.app.corrections.add("2026-10-14", "08:00", "12:00", "written later", None, "Acme")
        outcome = self.f.app.labels.rename("Acme", "northwind")
        self.assertEqual(self.labels_of_shifts(), ["Northwind", "Northwind"])
        self.assertTrue(outcome.message.startswith("merged Acme into Northwind"))

    def test_the_readable_folder_follows_a_rename(self):
        self.f.app.labels.rename("Northwind", "Northwind Ltd")
        self.assertTrue((self.f.data / "Northwind Ltd" / "Days" / "2026-10-13.md").exists())
        self.assertFalse((self.f.data / "Northwind").exists())


class LabellingAShift(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:03:00")
        self.f.app.setup.configure("12:00 for 60 min", "08:00 to 17:00")
        self.f.app.clocking.clock_in(None, None, "Acme")

    def test_a_label_change_stays_on_the_record(self):
        self.f.at("2026-10-14T12:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.app.labels.label_shift(self.f.app.log.shifts()[0].id, "Globex")
        shift = self.f.app.log.shifts()[0]
        self.assertEqual(shift.label, "Globex")
        self.assertIn("label changed from Acme to Globex", shift.changes[-1])


class TheDefaultLabel(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure("12:00 for 60 min", "08:00 to 17:00", "Northwind")

    def test_the_default_takes_the_existing_spelling(self):
        self.f.app.clocking.clock_in(None, None, "Acme", off_default=True)
        self.f.app.labels.set_default("ACME")
        self.assertEqual(self.f.app.log.working_day.default_label, "Acme")

    def test_renaming_the_default_label_keeps_it_the_default(self):
        self.f.app.clocking.clock_in(None, None)
        self.f.app.labels.rename("Northwind", "Northwind Ltd")
        self.assertEqual(self.f.app.log.working_day.default_label, "Northwind Ltd")


if __name__ == "__main__":
    unittest.main()
