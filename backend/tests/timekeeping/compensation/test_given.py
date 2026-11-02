import unittest
from datetime import timedelta

from chronata.timekeeping.compensation.given import Payment, TimeOff, given_in


class WhatWasGiven(unittest.TestCase):
    def test_a_payment_counts_as_paid_and_not_as_time_off(self):
        self.assertEqual((Payment(1.5).paid, Payment(1.5).time_off), (timedelta(hours=1, minutes=30), timedelta()))

    def test_time_off_counts_as_time_off_and_not_as_paid(self):
        self.assertEqual((TimeOff(2).paid, TimeOff(2).time_off), (timedelta(), timedelta(hours=2)))

    def test_each_kind_is_read_back_from_what_the_log_holds(self):
        self.assertEqual(given_in({"kind": "time_off", "hours": 2, "reference": "leave form"}), TimeOff(2, "leave form"))
        self.assertEqual(given_in({"kind": "paid", "hours": 1}), Payment(1))


if __name__ == "__main__":
    unittest.main()
