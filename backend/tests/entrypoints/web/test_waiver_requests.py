import unittest
from types import SimpleNamespace
from unittest.mock import create_autospec

from chronata.entrypoints.web.requests import changes
from chronata.use_cases.corrections.corrections import Corrections
from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.waivers.waivers import Waivers


def app_with_waivers() -> SimpleNamespace:
    return SimpleNamespace(waivers=create_autospec(Waivers, instance=True))


class TheWaiverRequests(unittest.TestCase):
    def test_waiving_passes_the_day_and_stretch_on(self):
        app = app_with_waivers()
        changes(app)["/api/waive"]({"ids": [5, 6], "start": "17:30", "end": "23:10", "reason": "forgot"})
        app.waivers.waive.assert_called_once_with([5, 6], "17:30", "23:10", "forgot")

    def test_counting_again_passes_the_waiver_on(self):
        app = app_with_waivers()
        changes(app)["/api/withdraw-waiver"]({"id": 5, "start": "2026-10-14T17:30:00+02:00", "reason": "was working"})
        app.waivers.withdraw.assert_called_once_with(5, "2026-10-14T17:30:00+02:00", "was working")

    def test_counting_again_without_a_shift_number_is_refused(self):
        app = app_with_waivers()
        bodies = [{"start": "17:30", "reason": "x"}, {"id": "5", "start": "17:30", "reason": "x"}, {"id": True, "start": "17:30", "reason": "x"}]
        for body in bodies:
            with self.subTest(body=body), self.assertRaises(UserError):
                changes(app)["/api/withdraw-waiver"](body)
        app.waivers.withdraw.assert_not_called()

    def test_waiving_with_shift_numbers_that_are_not_whole_numbers_is_refused(self):
        app = app_with_waivers()
        for ids in ("1", 5, [True], [1.5], None):
            with self.subTest(ids=ids), self.assertRaises(UserError):
                changes(app)["/api/waive"]({"ids": ids, "start": "17:30", "end": "23:10", "reason": "forgot"})
        app.waivers.waive.assert_not_called()

    def test_waiving_with_a_reason_that_is_not_text_is_refused(self):
        app = app_with_waivers()
        with self.assertRaises(UserError):
            changes(app)["/api/waive"]({"ids": [5], "start": "17:30", "end": "23:10", "reason": 5})
        app.waivers.waive.assert_not_called()



class TheExplainRequest(unittest.TestCase):
    def test_a_shift_number_that_is_not_a_whole_number_is_refused(self):
        app = SimpleNamespace(corrections=create_autospec(Corrections, instance=True))
        for given in (True, 5.9, "5"):
            with self.subTest(given=given), self.assertRaises(UserError):
                changes(app)["/api/explain"]({"id": given, "start": "2026-10-14T12:00:00+02:00", "reason": "power cut"})
        app.corrections.explain_break.assert_not_called()


if __name__ == "__main__":
    unittest.main()
