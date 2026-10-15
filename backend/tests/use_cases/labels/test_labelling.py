import unittest

from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions.questions import Answers, LabelNeedsHours, UnconfirmedLabel
from tests.fakes import Fixture, hours


class Labels(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T17:00:00")
        for label in ("Northwind", "Acme"):
            self.f.app.labels.create(label, Answers(no_set_hours=True))
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
        with self.assertRaises(LabelNeedsHours):
            self.f.app.corrections.add("2026-10-14", "08:00", "12:00", "written later", None, "Northwnid", answers=Answers(new_label=True))
        self.f.app.labels.create("Northwnid", hours("09:00", "15:00", new_label=True))
        self.f.app.corrections.add("2026-10-14", "08:00", "12:00", "written later", None, "Northwnid")
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

    def test_renaming_onto_a_label_with_no_shifts_yet_merges_into_its_spelling(self):
        outcome = self.f.app.labels.rename("Northwind", "acme")
        self.assertEqual(self.labels_of_shifts(), ["Acme"])
        self.assertTrue(outcome.message.startswith("merged Northwind into Acme"))

    def test_a_label_with_no_shifts_yet_can_be_renamed(self):
        self.f.app.labels.rename("Acme", "Acme Ltd")
        self.assertEqual(self.f.app.log.hours.labels(), ["Northwind", "Acme Ltd"])

    def test_the_readable_folder_follows_a_rename(self):
        self.f.app.labels.rename("Northwind", "Northwind Ltd")
        self.assertTrue((self.f.data / "Northwind Ltd" / "Days" / "2026-10-13.md").exists())
        self.assertFalse((self.f.data / "Northwind").exists())


class LabellingAShift(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:03:00")
        self.f.app.setup.configure(hours("08:00", "17:00", "12:00", "60"))
        for label in ("Acme", "Globex"):
            self.f.app.labels.create(label, Answers(no_set_hours=True))
        self.f.app.clocking.clock_in(None, None, "Acme")

    def test_a_label_change_stays_on_the_record(self):
        self.f.at("2026-10-14T12:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.app.labels.label_shifts([self.f.app.log.shifts()[0].id], "Globex")
        shift = self.f.app.log.shifts()[0]
        self.assertEqual(shift.label, "Globex")
        self.assertIn("label changed from Acme to Globex", shift.changes[-1])


class TheDefaultLabel(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00", "12:00", "60"), "Northwind")
        self.f.app.labels.create("Acme", Answers(no_set_hours=True))

    def test_the_default_takes_the_existing_spelling(self):
        self.f.app.clocking.clock_in(None, None, "Acme", Answers(off_default=True))
        self.f.app.labels.set_default("ACME")
        self.assertEqual(self.f.app.log.hours.default_label, "Acme")

    def test_renaming_the_default_label_keeps_it_the_default(self):
        self.f.app.clocking.clock_in(None, None)
        self.f.app.labels.rename("Northwind", "Northwind Ltd")
        self.assertEqual(self.f.app.log.hours.default_label, "Northwind Ltd")


class NewLabelsComeWithTheirHours(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure(hours("08:30", "17:30", "12:00", "60"), "Northwind")

    def test_clocking_in_on_a_brand_new_label_asks_for_its_hours_and_records_nothing(self):
        with self.assertRaises(LabelNeedsHours) as raised:
            self.f.app.clocking.clock_in(None, None, "Globex", Answers(off_default=True))
        self.assertEqual((raised.exception.label, self.f.app.log.shifts()), ("Globex", []))

    def test_its_hours_can_come_with_the_clock_in_itself(self):
        self.f.app.clocking.clock_in(None, None, "Globex", hours("09:00", "15:00", off_default=True))
        self.assertEqual((self.f.app.log.shifts()[0].label, self.f.app.log.hours.for_label("Globex").daily_hours), ("Globex", 6))

    def test_once_created_it_just_starts_and_keeps_its_own_hours(self):
        self.f.app.labels.create("Globex", hours("09:00", "15:00"))
        self.f.app.clocking.clock_in(None, None, "globex", Answers(off_default=True))
        globex = self.f.app.log.hours.for_label("Globex")
        self.assertEqual((self.f.app.log.shifts()[0].label, globex.daily_hours, globex.lunch), ("Globex", 6, None))
        self.assertEqual(self.f.app.log.hours.main.daily_hours, 8)

    def test_a_label_can_have_no_set_hours(self):
        self.f.app.labels.create("Freelance", Answers(no_set_hours=True))
        self.assertIn("Freelance", self.f.app.log.hours.labels())
        self.assertIsNone(self.f.app.log.hours.for_label("Freelance"))

    def test_an_existing_label_cannot_be_created_twice(self):
        with self.assertRaises(UserError):
            self.f.app.labels.create("northwind", hours("09:00", "15:00"))

    def test_renaming_a_label_keeps_its_hours(self):
        self.f.app.labels.create("Globex", hours("09:00", "15:00"))
        self.f.app.clocking.clock_in(None, None, "Globex", Answers(off_default=True))
        self.f.app.labels.rename("Globex", "Globex Ltd")
        self.assertEqual(self.f.app.log.hours.for_label("Globex Ltd").daily_hours, 6)


if __name__ == "__main__":
    unittest.main()
