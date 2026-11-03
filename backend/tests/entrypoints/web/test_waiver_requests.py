import unittest
from types import SimpleNamespace
from unittest.mock import create_autospec

from chronata.entrypoints.web.requests import changes
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
        for given in ({}, {"id": "5"}, {"id": True}):
            with self.subTest(given=given), self.assertRaises(UserError):
                changes(app)["/api/withdraw-waiver"]({**given, "start": "17:30", "reason": "x"})
        app.waivers.withdraw.assert_not_called()


if __name__ == "__main__":
    unittest.main()
