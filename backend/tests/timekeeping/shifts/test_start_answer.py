import unittest

from chronata.timekeeping.shifts.start_answer import StartAnswer, start_answer_in


class WhatTheLogKeeps(unittest.TestCase):
    def test_each_answer_is_read_back_as_it_was_given(self):
        for answer in (StartAnswer(late=True), StartAnswer(other_project=True), StartAnswer(overtime=True), StartAnswer(normal_hours=True)):
            self.assertEqual(start_answer_in(answer.data()), answer)

    def test_no_answer_leaves_nothing_in_the_log(self):
        self.assertEqual(StartAnswer().data(), {})

    def test_an_older_clock_in_without_answers_reads_as_no_answer(self):
        self.assertEqual(start_answer_in({"at": "2026-10-05T08:00:00+02:00", "boot": "b"}), StartAnswer())


if __name__ == "__main__":
    unittest.main()
