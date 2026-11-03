import unittest
from dataclasses import fields

from chronata.use_cases.questions.questions import ANSWER_KINDS, Answers


class EveryAnswerHasAKind(unittest.TestCase):
    def test_each_answer_field_has_a_kind_its_refusal_can_name(self):
        unnamed = []
        for answer in fields(Answers):
            if answer.type not in ANSWER_KINDS:
                unnamed.append(answer.name)
        self.assertEqual(unnamed, [])


if __name__ == "__main__":
    unittest.main()
