import unittest
from unittest.mock import create_autospec

from chronata.entrypoints.cli.main import parser
from chronata.use_cases.waivers.waivers import Waivers
from chronata.wiring import App


def run(typed: list[str]) -> App:
    app = create_autospec(App, instance=True)
    app.waivers = create_autospec(Waivers, instance=True)
    args = parser().parse_args(typed)
    args.run(args, app)
    return app


class TheWaiverCommands(unittest.TestCase):
    def test_waive_passes_the_shift_and_stretch_on(self):
        app = run(["waive", "7", "17:30", "23:10", "--reason", "forgot to clock out"])
        app.waivers.waive.assert_called_once_with([7], "17:30", "23:10", "forgot to clock out")

    def test_unwaive_passes_the_waiver_on(self):
        app = run(["unwaive", "7", "2026-10-14T17:30:00+02:00", "--reason", "was working"])
        app.waivers.withdraw.assert_called_once_with(7, "2026-10-14T17:30:00+02:00", "was working")


if __name__ == "__main__":
    unittest.main()
