import unittest

from chronata.use_cases.outcome import UserError
from tests.fakes import Fixture


class SettingUpTheWorkingDay(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure("12:00 for 60 min", "08:00 to 17:00", "Northwind")

    def test_setting_up_the_working_day(self):
        self.f.app.setup.configure("12h30 for 30 min", "07:30 to 16:00")
        self.assertEqual(self.f.app.log.working_day.daily_hours, 8.0)
        with self.assertRaises(UserError):
            self.f.app.setup.configure("12:00", "")

    def test_leaving_the_setup_answer_out_keeps_the_default(self):
        self.f.app.setup.configure("12:00 for 30 min", "08:00 to 16:30")
        self.assertEqual(self.f.app.log.working_day.default_label, "Northwind")


if __name__ == "__main__":
    unittest.main()
