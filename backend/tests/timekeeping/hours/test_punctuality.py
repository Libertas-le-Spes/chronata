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

    def test_arriving_late_alone_is_worth_noting(self):
        self.assertTrue(Punctuality(timedelta(minutes=10)).worth_noting)

    def test_leaving_early_alone_is_worth_noting(self):
        self.assertTrue(Punctuality(timedelta(), timedelta(minutes=10)).worth_noting)

    def test_arriving_on_time_is_nothing_to_make_up(self):
        self.assertEqual((Punctuality().made_up, Punctuality().worth_noting), (False, False))


class LatenessNotCovered(unittest.TestCase):
    def test_late_and_leaving_on_time_leaves_all_of_it_uncovered(self):
        self.assertEqual(Punctuality(timedelta(minutes=12), timedelta(minutes=12)).uncovered_lateness, timedelta(minutes=12))

    def test_staying_a_little_later_covers_part_of_it(self):
        self.assertEqual(Punctuality(timedelta(minutes=12), timedelta(minutes=7)).uncovered_lateness, timedelta(minutes=7))

    def test_staying_long_enough_covers_all_of_it(self):
        self.assertEqual(Punctuality(timedelta(minutes=12)).uncovered_lateness, timedelta())

    def test_leaving_early_as_well_counts_only_the_lateness(self):
        self.assertEqual(Punctuality(timedelta(minutes=12), timedelta(minutes=22)).uncovered_lateness, timedelta(minutes=12))

    def test_leaving_early_after_arriving_on_time_is_not_lateness(self):
        self.assertEqual(Punctuality(timedelta(), timedelta(minutes=30)).uncovered_lateness, timedelta())


if __name__ == "__main__":
    unittest.main()
