import unittest
from types import SimpleNamespace
from unittest.mock import create_autospec

from chronata.entrypoints.web.requests import changes
from chronata.use_cases.corrections.corrections import Corrections
from chronata.use_cases.questions.questions import Answers


class TheCorrectRequest(unittest.TestCase):
    def test_its_answers_reach_the_correction(self):
        app = SimpleNamespace(corrections=create_autospec(Corrections, instance=True))
        changes(app)["/api/correct"]({"ids": [5], "start": "18:30", "end": "20:30", "reason": "moved", "answers": {"overtime": True}})
        app.corrections.correct.assert_called_once_with([5], "18:30", "20:30", "moved", Answers(overtime=True))


if __name__ == "__main__":
    unittest.main()
