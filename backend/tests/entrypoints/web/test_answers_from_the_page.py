import unittest
from types import SimpleNamespace
from unittest.mock import create_autospec

from chronata.entrypoints.web.requests import changes
from chronata.use_cases.clocking.clocking import Clocking
from chronata.use_cases.hours.working_day_setup import WorkingDaySetup
from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions.questions import Answers


class AnswersFromThePage(unittest.TestCase):
    def setUp(self):
        self.app = SimpleNamespace(clocking=create_autospec(Clocking, instance=True))
        self.clock_in = changes(self.app)["/api/in"]

    def given(self) -> Answers:
        return self.app.clocking.clock_in.call_args.args[3]

    def test_answers_are_taken_from_the_answers_section(self):
        self.clock_in({"label": "Secondary", "answers": {"off_default": True}})
        self.assertTrue(self.given().off_default)

    def test_a_field_outside_the_answers_section_is_not_taken_as_an_answer(self):
        self.clock_in({"label": "Secondary", "off_default": True})
        self.assertFalse(self.given().off_default)

    def test_answers_that_are_not_named_answers_are_refused(self):
        with self.assertRaises(UserError):
            self.clock_in({"label": "Secondary", "answers": ["off_default"]})
        self.app.clocking.clock_in.assert_not_called()


class TheSetupForm(unittest.TestCase):
    def test_the_hours_typed_in_reach_the_setup_as_answers(self):
        app = SimpleNamespace(setup=create_autospec(WorkingDaySetup, instance=True))
        changes(app)["/api/setup"]({"label": "Primary", "answers": {"shift_start": "08:00", "shift_end": "17:00"}})
        app.setup.configure.assert_called_once_with(Answers(shift_start="08:00", shift_end="17:00"), "Primary")


if __name__ == "__main__":
    unittest.main()
