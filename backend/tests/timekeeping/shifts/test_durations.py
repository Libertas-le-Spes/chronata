import unittest
from datetime import timedelta

from chronata.timekeeping.shifts.durations import hours


class ShowingHours(unittest.TestCase):
    def test_hours_and_minutes(self):
        self.assertEqual(hours(timedelta(hours=72, minutes=7)), "72:07")

    def test_a_negative_span_keeps_its_minutes_and_shows_a_minus(self):
        self.assertEqual(hours(timedelta(minutes=-2)), "-0:02")

    def test_a_negative_span_over_an_hour(self):
        self.assertEqual(hours(timedelta(hours=-1, minutes=-5)), "-1:05")


if __name__ == "__main__":
    unittest.main()
