import unittest
from types import SimpleNamespace
from unittest.mock import create_autospec

from chronata.entrypoints.cli.main import parser
from chronata.use_cases.clocking.clocking import Clocking


class TheClockInCommand(unittest.TestCase):
    def given_answers(self, typed: list[str]):
        app = SimpleNamespace(clocking=create_autospec(Clocking, instance=True))
        args = parser().parse_args(["in"] + typed)
        args.run(args, app)
        return app.clocking.clock_in.call_args.args[3]

    def test_late_is_passed_on(self):
        self.assertTrue(self.given_answers(["--label", "Secondary", "--late"]).late)

    def test_another_project_is_passed_on(self):
        self.assertTrue(self.given_answers(["--label", "Secondary", "--other-project"]).other_project)

    def test_overtime_is_passed_on(self):
        self.assertTrue(self.given_answers(["--overtime"]).overtime)

    def test_normal_hours_is_passed_on(self):
        self.assertTrue(self.given_answers(["--normal-hours"]).normal_hours)


if __name__ == "__main__":
    unittest.main()
