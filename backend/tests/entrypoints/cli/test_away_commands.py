import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import create_autospec

from chronata.entrypoints.cli.main import parser
from chronata.use_cases.away.away import Away
from chronata.wiring import App


def run(typed: list[str]) -> App:
    app = create_autospec(App, instance=True)
    app.away = create_autospec(Away, instance=True)
    args = parser().parse_args(typed)
    args.run(args, app)
    return app


class TheAwayCommands(unittest.TestCase):
    def test_away_passes_how_long_there_was_no_input(self):
        run(["away", "600"]).away.began.assert_called_once_with(600)

    def test_an_idle_time_that_is_not_seconds_in_a_day_is_refused(self):
        for typed in ("-1", "86401", "1000000000000", "ten"):
            with self.subTest(typed=typed), self.assertRaises(SystemExit), redirect_stderr(StringIO()):
                parser().parse_args(["away", typed])

    def test_the_edges_are_allowed(self):
        for seconds in (0, 86400):
            with self.subTest(seconds=seconds):
                run(["away", str(seconds)]).away.began.assert_called_once_with(seconds)

    def test_back_notes_the_return(self):
        run(["back"]).away.ended.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
