import unittest
from datetime import time

from chronata.use_cases import typed_input
from chronata.use_cases.outcome import UserError


class SetupAnswers(unittest.TestCase):
    def test_blank_answers_take_the_defaults(self):
        self.assertEqual(typed_input.lunch(""), (time(12), 60))
        self.assertEqual(typed_input.shift(""), (time(8), time(17)))

    def test_the_ways_people_write_times(self):
        self.assertEqual(typed_input.lunch("12h30 for 45 min"), (time(12, 30), 45))
        self.assertEqual(typed_input.lunch("13:00 1h30"), (time(13), 90))
        self.assertEqual(typed_input.shift("08h00 to 17h00"), (time(8), time(17)))
        self.assertEqual(typed_input.shift("9am-5pm"), (time(9), time(17)))

    def test_nonsense_is_refused_with_a_reason(self):
        for bad in ("12:00", "lunch"):
            with self.assertRaises(UserError):
                typed_input.lunch(bad)


if __name__ == "__main__":
    unittest.main()
