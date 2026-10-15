import unittest

from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions.questions import Answers
from tests.fakes import Fixture, hours


class SettingUpTheWorkingDay(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00", "12:00", "60"), "Northwind")

    def test_setting_up_the_working_day(self):
        self.f.app.setup.configure(hours("07:30", "16:00", "12:30", "30"))
        self.assertEqual(self.f.app.log.hours.main.daily_hours, 8.0)
        with self.assertRaises(UserError):
            self.f.app.setup.configure(hours("", "17:00"))

    def test_leaving_the_setup_answer_out_keeps_the_default(self):
        self.f.app.setup.configure(hours("08:00", "16:30", "12:00", "30"))
        self.assertEqual(self.f.app.log.hours.default_label, "Northwind")


class ChangingALabelsHours(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure(hours("08:30", "17:30", "12:00", "60"), "Northwind")

    def test_lunch_is_optional(self):
        self.f.app.setup.set_hours("Northwind", hours("08:00", "16:00"))
        northwind = self.f.app.log.hours.main
        self.assertEqual((northwind.lunch, northwind.daily_hours), (None, 8))

    def test_a_label_can_be_set_to_no_set_hours(self):
        self.f.app.setup.set_hours("Northwind", Answers(no_set_hours=True))
        self.assertIsNone(self.f.app.log.hours.main)

    def test_hours_for_a_label_that_does_not_exist_are_refused(self):
        with self.assertRaises(UserError):
            self.f.app.setup.set_hours("Nobody", hours("09:00", "17:00"))


if __name__ == "__main__":
    unittest.main()
