import unittest
from datetime import timedelta

from chronata.timekeeping.hours.weekly_allowance import WeeklyAllowance

FULL_DAY = timedelta(hours=8)


class UsingUpTheWeek(unittest.TestCase):
    def test_a_long_day_counts_only_a_full_day_as_normal(self):
        self.assertEqual(WeeklyAllowance(timedelta(hours=40)).normal_part(timedelta(hours=10), FULL_DAY), FULL_DAY)

    def test_a_short_day_counts_all_of_it_as_normal(self):
        self.assertEqual(WeeklyAllowance(timedelta(hours=40)).normal_part(timedelta(hours=5), FULL_DAY), timedelta(hours=5))

    def test_once_the_week_is_nearly_used_up_only_what_is_left_is_normal(self):
        self.assertEqual(WeeklyAllowance(timedelta(hours=3)).normal_part(timedelta(hours=8), FULL_DAY), timedelta(hours=3))

    def test_each_day_uses_up_its_normal_hours(self):
        self.assertEqual(WeeklyAllowance(timedelta(hours=40)).after(FULL_DAY), WeeklyAllowance(timedelta(hours=32)))


if __name__ == "__main__":
    unittest.main()
