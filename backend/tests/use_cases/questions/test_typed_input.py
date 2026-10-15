import unittest
from datetime import time

from chronata.timekeeping.hours.working_day import Lunch
from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions import typed_input


class SetupAnswers(unittest.TestCase):
    def test_a_blank_shift_takes_the_default_and_a_blank_lunch_means_none(self):
        self.assertEqual(typed_input.shift(""), (time(8), time(17)))
        for none in ("", "none", "No lunch", "0:00 for 0 min"):
            self.assertIsNone(typed_input.lunch(none), none)

    def test_the_ways_people_write_times(self):
        self.assertEqual(typed_input.lunch("12h30 for 45 min"), Lunch(time(12, 30), 45))
        self.assertEqual(typed_input.lunch("13:00 1h30"), Lunch(time(13), 90))
        self.assertEqual(typed_input.shift("08h00 to 17h00"), (time(8), time(17)))
        self.assertEqual(typed_input.shift("9am-5pm"), (time(9), time(17)))

    def test_nonsense_is_refused_with_a_reason(self):
        for bad in ("12:00", "lunch"):
            with self.assertRaises(UserError):
                typed_input.lunch(bad)


if __name__ == "__main__":
    unittest.main()
