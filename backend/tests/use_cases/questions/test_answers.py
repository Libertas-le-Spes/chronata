import unittest

from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions.questions import Answers


class AnswersFromThePage(unittest.TestCase):
    def test_a_yes_or_no_answer_that_is_not_true_or_false_is_refused(self):
        with self.assertRaises(UserError):
            Answers.from_dict({"overtime": "no"})

    def test_true_and_false_are_taken_as_given(self):
        self.assertEqual(Answers.from_dict({"overtime": True, "late": False}), Answers(overtime=True))

    def test_text_answers_stay_text(self):
        self.assertEqual(Answers.from_dict({"shift_start": "0830"}).shift_start, "0830")


if __name__ == "__main__":
    unittest.main()
