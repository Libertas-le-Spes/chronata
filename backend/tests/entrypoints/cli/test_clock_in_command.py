import unittest
from unittest.mock import create_autospec

from chronata.entrypoints.cli.main import parser
from chronata.use_cases.clocking.clocking import Clocking
from chronata.use_cases.corrections.corrections import Corrections
from chronata.wiring import App


CLOCK_IN_ANSWERS = 3
ADD_ANSWERS = 6
CORRECT_ANSWERS = 4


class TheClockInCommand(unittest.TestCase):
    def given_answers(self, typed: list[str]):
        app = create_autospec(App, instance=True)
        app.clocking = create_autospec(Clocking, instance=True)
        args = parser().parse_args(["in"] + typed)
        args.run(args, app)
        app.clocking.clock_in.assert_called_once()
        return app.clocking.clock_in.call_args.args[CLOCK_IN_ANSWERS]

    def test_late_is_passed_on(self):
        self.assertTrue(self.given_answers(["--label", "Secondary", "--late"]).late)

    def test_another_project_is_passed_on(self):
        self.assertTrue(self.given_answers(["--label", "Secondary", "--other-project"]).other_project)

    def test_overtime_is_passed_on(self):
        self.assertTrue(self.given_answers(["--overtime"]).overtime)

    def test_normal_hours_is_passed_on(self):
        self.assertTrue(self.given_answers(["--normal-hours"]).normal_hours)


class TheAddCommand(unittest.TestCase):
    def given_answers(self, typed: list[str]):
        app = create_autospec(App, instance=True)
        app.corrections = create_autospec(Corrections, instance=True)
        args = parser().parse_args(["add", "2026-10-14", "18:00", "20:00", "--reason", "forgot to clock in"] + typed)
        args.run(args, app)
        app.corrections.add.assert_called_once()
        return app.corrections.add.call_args.args[ADD_ANSWERS]

    def test_overtime_is_passed_on(self):
        self.assertTrue(self.given_answers(["--overtime"]).overtime)

    def test_late_is_passed_on(self):
        self.assertTrue(self.given_answers(["--label", "Secondary", "--late"]).late)


class TheCorrectCommand(unittest.TestCase):
    def test_overtime_is_passed_on(self):
        app = create_autospec(App, instance=True)
        app.corrections = create_autospec(Corrections, instance=True)
        args = parser().parse_args(["correct", "5", "--start", "18:30", "--reason", "moved", "--overtime"])
        args.run(args, app)
        app.corrections.correct.assert_called_once()
        self.assertTrue(app.corrections.correct.call_args.args[CORRECT_ANSWERS].overtime)


if __name__ == "__main__":
    unittest.main()
