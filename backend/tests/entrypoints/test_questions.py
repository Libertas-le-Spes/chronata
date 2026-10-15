import unittest

from chronata.entrypoints.cli.answers import how_to_answer
from chronata.entrypoints.web.refusals import refusal
from chronata.use_cases.questions.questions import Choice, Input, Question


class Pizza(Question):
    def __init__(self):
        super().__init__("Lunch is on us today. Which pizza?",
                         [Choice("Margherita", answers={"pizza": "margherita"}), Choice("Something else", inputs=(Input("pizza", "Which one?", "hawaiian"),))])


class AnyQuestionIsAskedTheSameWay(unittest.TestCase):
    def test_the_command_line_explains_a_question_it_has_never_seen(self):
        self.assertEqual(how_to_answer(Pizza()), "Lunch is on us today. Which pizza?\n"
                                                 "  Margherita: add --pizza 'margherita'\n"
                                                 "  Something else: add --pizza 'hawaiian'")

    def test_the_page_is_sent_a_question_it_has_never_seen(self):
        status, reply = refusal(Pizza())
        self.assertEqual((status, reply["question"]["text"], [c["caption"] for c in reply["question"]["choices"]]),
                         (409, "Lunch is on us today. Which pizza?", ["Margherita", "Something else"]))
