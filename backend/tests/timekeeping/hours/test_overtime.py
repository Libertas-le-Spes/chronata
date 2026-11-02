import unittest
from datetime import timedelta

from chronata.timekeeping.hours.overtime import Overtime, beyond, total


class MeasuringOvertime(unittest.TestCase):
    def test_overtime_is_what_was_worked_beyond_normal_hours(self):
        self.assertEqual(beyond(timedelta(hours=9, minutes=30), timedelta(hours=8)), Overtime(timedelta(hours=1, minutes=30)))

    def test_overtime_from_several_days_adds_up(self):
        days = [Overtime(timedelta(minutes=20)), Overtime(timedelta(minutes=40)), Overtime()]
        self.assertEqual(total(days), Overtime(timedelta(hours=1)))

    def test_a_day_without_overtime_earned_none(self):
        self.assertEqual((Overtime().earned_some, Overtime(timedelta(minutes=1)).earned_some), (False, True))


if __name__ == "__main__":
    unittest.main()
