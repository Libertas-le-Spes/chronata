import unittest

from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions.questions import Answers, LabelNeedsHours, UnconfirmedLabel
from tests.fakes import Fixture, hours


class Labels(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T17:00:00")
        for label in ("Primary", "Secondary"):
            self.f.app.labels.create(label, Answers(no_set_hours=True))
        self.f.app.corrections.add("2026-10-13", "08:00", "12:00", "written later", None, "Primary")

    def labels_of_shifts(self) -> list[str]:
        return [shift.label for shift in self.f.app.log.shifts()]

    def test_the_existing_spelling_is_used_whatever_the_capitals(self):
        self.f.app.corrections.add("2026-10-14", "08:00", "12:00", "written later", None, "primary ")
        self.assertEqual(self.labels_of_shifts(), ["Primary", "Primary"])

    def test_a_near_miss_needs_confirming_before_it_becomes_a_new_label(self):
        with self.assertRaises(UnconfirmedLabel) as raised:
            self.f.app.corrections.add("2026-10-14", "08:00", "12:00", "written later", None, "Primray")
        self.assertEqual(raised.exception.near_misses, ("Primary",))
        with self.assertRaises(LabelNeedsHours):
            self.f.app.corrections.add("2026-10-14", "08:00", "12:00", "written later", None, "Primray", answers=Answers(new_label=True))
        self.f.app.labels.create("Primray", hours("09:00", "15:00", new_label=True))
        self.f.app.corrections.add("2026-10-14", "08:00", "12:00", "written later", None, "Primray")
        self.assertIn("Primray", self.labels_of_shifts())

    def test_renaming_moves_every_shift_and_stays_on_the_record(self):
        self.f.app.corrections.add("2026-10-14", "08:00", "12:00", "written later", None, "Primary")
        outcome = self.f.app.labels.rename("primary", "Primary Ltd")
        self.assertEqual(self.labels_of_shifts(), ["Primary Ltd", "Primary Ltd"])
        self.assertIn("on 2 shifts", outcome.message)
        self.assertIn("label changed from Primary to Primary Ltd", self.f.app.log.shifts()[0].changes[-1])

    def test_renaming_onto_an_existing_label_merges_them(self):
        self.f.app.corrections.add("2026-10-14", "08:00", "12:00", "written later", None, "Secondary")
        outcome = self.f.app.labels.rename("Secondary", "primary")
        self.assertEqual(self.labels_of_shifts(), ["Primary", "Primary"])
        self.assertTrue(outcome.message.startswith("merged Secondary into Primary"))

    def test_renaming_onto_a_label_with_no_shifts_yet_merges_into_its_spelling(self):
        outcome = self.f.app.labels.rename("Primary", "secondary")
        self.assertEqual(self.labels_of_shifts(), ["Secondary"])
        self.assertTrue(outcome.message.startswith("merged Primary into Secondary"))

    def test_a_label_with_no_shifts_yet_can_be_renamed(self):
        self.f.app.labels.rename("Secondary", "Secondary Ltd")
        self.assertEqual(self.f.app.log.hours.labels(), ["Primary", "Secondary Ltd"])

    def test_the_readable_folder_follows_a_rename(self):
        self.f.app.labels.rename("Primary", "Primary Ltd")
        self.assertTrue((self.f.data / "Primary Ltd" / "Days" / "2026-10-13.md").exists())
        self.assertFalse((self.f.data / "Primary").exists())


class LabellingAShift(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:03:00")
        self.f.app.setup.configure(hours("08:00", "17:00", "12:00", "60"))
        for label in ("Secondary", "Tertiary"):
            self.f.app.labels.create(label, Answers(no_set_hours=True))
        self.f.app.clocking.clock_in(None, None, "Secondary")

    def test_a_label_change_stays_on_the_record(self):
        self.f.at("2026-10-14T12:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.app.labels.label_shifts([self.f.app.log.shifts()[0].id], "Tertiary")
        shift = self.f.app.log.shifts()[0]
        self.assertEqual(shift.label, "Tertiary")
        self.assertIn("label changed from Secondary to Tertiary", shift.changes[-1])


class TheDefaultLabel(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00", "12:00", "60"), "Primary")
        self.f.app.labels.create("Secondary", Answers(no_set_hours=True))

    def test_the_default_takes_the_existing_spelling(self):
        self.f.app.clocking.clock_in(None, None, "Secondary", Answers(off_default=True))
        self.f.app.labels.set_default("SECONDARY")
        self.assertEqual(self.f.app.log.hours.default_label, "Secondary")

    def test_renaming_the_default_label_keeps_it_the_default(self):
        self.f.app.clocking.clock_in(None, None)
        self.f.app.labels.rename("Primary", "Primary Ltd")
        self.assertEqual(self.f.app.log.hours.default_label, "Primary Ltd")


class NewLabelsComeWithTheirHours(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure(hours("08:30", "17:30", "12:00", "60"), "Primary")

    def test_clocking_in_on_a_brand_new_label_asks_for_its_hours_and_records_nothing(self):
        with self.assertRaises(LabelNeedsHours) as raised:
            self.f.app.clocking.clock_in(None, None, "Tertiary", Answers(off_default=True))
        self.assertEqual((raised.exception.label, self.f.app.log.shifts()), ("Tertiary", []))

    def test_its_hours_can_come_with_the_clock_in_itself(self):
        self.f.app.clocking.clock_in(None, None, "Tertiary", hours("09:00", "15:00", off_default=True))
        self.assertEqual((self.f.app.log.shifts()[0].label, self.f.app.log.hours.for_label("Tertiary").daily_hours), ("Tertiary", 6))

    def test_once_created_it_just_starts_and_keeps_its_own_hours(self):
        self.f.app.labels.create("Tertiary", hours("09:00", "15:00"))
        self.f.app.clocking.clock_in(None, None, "tertiary", Answers(off_default=True))
        tertiary = self.f.app.log.hours.for_label("Tertiary")
        self.assertEqual((self.f.app.log.shifts()[0].label, tertiary.daily_hours, tertiary.lunch), ("Tertiary", 6, None))
        self.assertEqual(self.f.app.log.hours.main.daily_hours, 8)

    def test_a_label_can_have_no_set_hours(self):
        self.f.app.labels.create("Freelance", Answers(no_set_hours=True))
        self.assertIn("Freelance", self.f.app.log.hours.labels())
        self.assertIsNone(self.f.app.log.hours.for_label("Freelance"))

    def test_an_existing_label_cannot_be_created_twice(self):
        with self.assertRaises(UserError):
            self.f.app.labels.create("primary", hours("09:00", "15:00"))

    def test_renaming_a_label_keeps_its_hours(self):
        self.f.app.labels.create("Tertiary", hours("09:00", "15:00"))
        self.f.app.clocking.clock_in(None, None, "Tertiary", Answers(off_default=True))
        self.f.app.labels.rename("Tertiary", "Tertiary Ltd")
        self.assertEqual(self.f.app.log.hours.for_label("Tertiary Ltd").daily_hours, 6)


if __name__ == "__main__":
    unittest.main()
