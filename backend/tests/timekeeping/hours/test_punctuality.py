import unittest
from datetime import timedelta

from chronata.timekeeping.hours.punctuality import Punctuality, judged

GRACE = timedelta(minutes=7)


class Judging(unittest.TestCase):
    def test_leaving_within_the_grace_after_arriving_on_time_is_forgiven(self):
        self.assertEqual(judged(timedelta(), timedelta(minutes=7), GRACE), Punctuality())

    def test_leaving_past_the_grace_is_short(self):
        self.assertEqual(judged(timedelta(), timedelta(minutes=8), GRACE), Punctuality(timedelta(), timedelta(minutes=8)))

    def test_after_arriving_late_no_shortfall_is_forgiven(self):
        self.assertEqual(judged(timedelta(minutes=2), timedelta(minutes=3), GRACE), Punctuality(timedelta(minutes=2), timedelta(minutes=3)))


class MakingUp(unittest.TestCase):
    def test_a_late_start_with_nothing_short_is_made_up(self):
        self.assertTrue(Punctuality(timedelta(minutes=10)).made_up)

    def test_a_late_start_still_short_is_not_made_up(self):
        self.assertFalse(Punctuality(timedelta(minutes=10), timedelta(minutes=4)).made_up)

    def test_arriving_on_time_is_nothing_to_make_up(self):
        self.assertEqual((Punctuality().made_up, Punctuality().worth_noting), (False, False))


if __name__ == "__main__":
    unittest.main()
