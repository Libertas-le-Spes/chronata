import unittest
from types import SimpleNamespace
from unittest.mock import ANY, create_autospec

from chronata.entrypoints.cli.main import parser
from chronata.use_cases.compensation.compensations import Compensations

PERIOD = ["compensation", "2026-10-01", "2026-10-31", "2"]


class TheCompensationCommand(unittest.TestCase):
    def setUp(self):
        self.app = SimpleNamespace(compensations=create_autospec(Compensations, instance=True))

    def recorded_kind(self, typed: list[str]) -> str:
        args = parser().parse_args(typed)
        args.run(args, self.app)
        return self.app.compensations.record.call_args.args[4]

    def test_without_the_flag_it_is_recorded_as_paid(self):
        self.assertEqual(self.recorded_kind(PERIOD), "paid")

    def test_with_time_off_it_is_recorded_as_time_off(self):
        self.assertEqual(self.recorded_kind(PERIOD + ["--time-off"]), "time_off")

    def test_the_period_and_hours_are_passed_on_once(self):
        args = parser().parse_args(PERIOD + ["--label", "Secondary", "--ref", "payslip"])
        args.run(args, self.app)
        self.app.compensations.record.assert_called_once_with("Secondary", "2026-10-01", "2026-10-31", 2.0, "paid", "payslip", ANY)
