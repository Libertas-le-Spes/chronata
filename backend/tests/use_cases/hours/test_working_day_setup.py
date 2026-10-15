import unittest

from chronata.use_cases.log.outcome import UserError
from tests.fakes import Fixture


class SettingUpTheWorkingDay(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure("12:00 for 60 min", "08:00 to 17:00", "Northwind")

    def test_setting_up_the_working_day(self):
        self.f.app.setup.configure("12h30 for 30 min", "07:30 to 16:00")
        self.assertEqual(self.f.app.log.hours.main.daily_hours, 8.0)
        with self.assertRaises(UserError):
            self.f.app.setup.configure("12:00", "")

    def test_leaving_the_setup_answer_out_keeps_the_default(self):
        self.f.app.setup.configure("12:00 for 30 min", "08:00 to 16:30")
        self.assertEqual(self.f.app.log.hours.default_label, "Northwind")


class ChangingALabelsHours(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure("12:00 for 60 min", "08:30 to 17:30", "Northwind")

    def test_lunch_is_optional(self):
        self.f.app.setup.set_hours("Northwind", "08:00 to 16:00", "")
        northwind = self.f.app.log.hours.main
        self.assertEqual((northwind.lunch, northwind.daily_hours), (None, 8))

    def test_a_label_can_be_set_to_no_set_hours(self):
        self.f.app.setup.set_hours("Northwind", "", "", no_set_hours=True)
        self.assertIsNone(self.f.app.log.hours.main)

    def test_hours_for_a_label_that_does_not_exist_are_refused(self):
        with self.assertRaises(UserError):
            self.f.app.setup.set_hours("Nobody", "09:00 to 17:00", "")


if __name__ == "__main__":
    unittest.main()
