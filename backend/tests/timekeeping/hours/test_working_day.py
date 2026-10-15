import unittest
from datetime import time

from chronata.timekeeping.hours.working_day import Lunch, WorkingDay, check_fits
from tests.fakes import at


def working_day() -> WorkingDay:
    return WorkingDay(time(8), time(17), Lunch(time(12), 60))


class FullDay(unittest.TestCase):
    def test_a_full_day_is_the_shift_less_lunch(self):
        self.assertEqual(working_day().daily_hours, 8)

    def test_without_lunch_the_whole_shift_is_the_day(self):
        no_lunch = WorkingDay(time(9), time(15))
        self.assertEqual((no_lunch.daily_hours, no_lunch.lunch_on(at("2026-10-14T09:00:00").date(), None)), (6, None))


class WorkdayBoundaries(unittest.TestCase):
    def test_only_a_clock_out_before_the_end_of_a_workday_needs_asking(self):
        self.assertTrue(working_day().before_end_of_workday(at("2026-10-14T14:20:00")))
        self.assertFalse(working_day().before_end_of_workday(at("2026-10-14T17:00:00")))
        self.assertFalse(working_day().before_end_of_workday(at("2026-10-17T14:20:00")))

    def test_a_shift_and_lunch_that_do_not_fit_are_refused(self):
        with self.assertRaises(ValueError):
            check_fits(time(17), time(8), Lunch(time(12), 60))
        with self.assertRaises(ValueError):
            check_fits(time(8), time(17), Lunch(time(18), 60))
        check_fits(time(9), time(15), None)


if __name__ == "__main__":
    unittest.main()
