import unittest
from datetime import time

from chronata.timekeeping.hours.working_day import Lunch, WorkingDay
from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions import typed_input
from tests.fakes import hours


class SetupAnswers(unittest.TestCase):
    def test_hours_from_the_four_setup_answers(self):
        self.assertEqual(typed_input.hours(hours("830", "1730", "1200", "45")), WorkingDay(time(8, 30), time(17, 30), Lunch(time(12), 45)))

    def test_the_page_sends_clock_times_and_seconds_are_dropped(self):
        self.assertEqual(typed_input.hours(hours("08:30:00", "17:30", "12:00", "45")).shift_start, time(8, 30))

    def test_an_empty_lunch_start_or_length_means_no_lunch(self):
        for lunch_start, minutes in (("", ""), ("", "45"), ("1200", "")):
            self.assertIsNone(typed_input.hours(hours("8", "17", lunch_start, minutes)).lunch, (lunch_start, minutes))

    def test_hours_that_do_not_fit_are_refused(self):
        for bad in (hours("", "17"), hours("17", "8"), hours("8", "17", "1800", "30"), hours("8", "9", "830", "120")):
            with self.assertRaises(UserError):
                typed_input.hours(bad)

    def test_times_typed_as_numbers(self):
        for typed, meant in (("8", time(8)), ("830", time(8, 30)), ("0830", time(8, 30)), ("17", time(17)), ("1730", time(17, 30)), (" 0 ", time(0))):
            self.assertEqual(typed_input.clock_number(typed), meant, typed)

    def test_anything_but_a_number_of_the_day_is_refused(self):
        for bad in ("", "8:30", "8h", "2400", "1260", "12345", "-5"):
            with self.assertRaises(UserError, msg=bad):
                typed_input.clock_number(bad)

    def test_lunch_minutes_are_a_plain_number(self):
        self.assertEqual(typed_input.minutes_number(" 45 "), 45)
        for bad in ("0", "241", "45 min", "", "1.5"):
            with self.assertRaises(UserError, msg=bad):
                typed_input.minutes_number(bad)


if __name__ == "__main__":
    unittest.main()
