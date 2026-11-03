import unittest
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

    def test_back_notes_the_return(self):
        run(["back"]).away.ended.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
