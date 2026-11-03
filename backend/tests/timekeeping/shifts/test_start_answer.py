import unittest

from chronata.timekeeping.shifts.start_answer import StartAnswer, start_answer_in


class WhatTheLogKeeps(unittest.TestCase):
    def test_each_answer_is_read_back_as_it_was_given(self):
        for answer in (StartAnswer(late=True), StartAnswer(late=False), StartAnswer(overtime_after_shift=True), StartAnswer(overtime_after_shift=False)):
            self.assertEqual(start_answer_in(answer.data()), answer)

    def test_no_answer_leaves_nothing_in_the_log(self):
        self.assertEqual(StartAnswer().data(), {})

    def test_an_older_clock_in_without_answers_reads_as_no_answer(self):
        self.assertEqual(start_answer_in({"at": "2026-10-05T08:00:00+02:00", "boot": "b"}), StartAnswer())


    def test_odd_values_in_the_log_read_as_no_answer(self):
        for odd in ({"late": "yes"}, {"late": 1}, {"late": None}, {"overtime_after_shift": "true"}, {"overtime_after_shift": [True]}):
            self.assertEqual(start_answer_in(odd), StartAnswer(), odd)


if __name__ == "__main__":
    unittest.main()
