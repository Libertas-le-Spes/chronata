import unittest
from datetime import date, timedelta

from chronata.timekeeping.hours.week import Week, latest_weeks, week_starting

MONDAYS = [date(2026, 9, 7) + timedelta(weeks=count) for count in range(4)]
FOUR_WEEKS = [Week(monday, ()) for monday in MONDAYS]


class RecentWeeks(unittest.TestCase):
    def test_only_the_latest_weeks_are_kept_oldest_first(self):
        self.assertEqual([week.start for week in latest_weeks(FOUR_WEEKS, 2)], [MONDAYS[2], MONDAYS[3]])

    def test_asking_for_more_weeks_than_there_are_keeps_them_all(self):
        self.assertEqual(latest_weeks(FOUR_WEEKS, 9), FOUR_WEEKS)


class WeekStart(unittest.TestCase):
    def test_a_week_starts_on_the_monday_before(self):
        self.assertEqual(week_starting(date(2026, 9, 10)), MONDAYS[0])


if __name__ == "__main__":
    unittest.main()
