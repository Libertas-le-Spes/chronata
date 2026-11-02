import unittest
from types import SimpleNamespace
from unittest.mock import ANY, create_autospec

from chronata.entrypoints.web.requests import changes
from chronata.use_cases.compensation.compensations import Compensations

FORM = {"label": "Acme", "from": "2026-10-01", "to": "2026-10-31", "hours": "1.5", "reference": "leave form"}


class TheCompensationForm(unittest.TestCase):
    def setUp(self):
        self.app = SimpleNamespace(compensations=create_autospec(Compensations, instance=True))

    def test_the_kind_chosen_on_the_page_is_what_gets_recorded(self):
        filled_in = dict(FORM)
        filled_in["kind"] = "time_off"
        changes(self.app)["/api/compensation"](filled_in)
        self.app.compensations.record.assert_called_once_with("Acme", "2026-10-01", "2026-10-31", 1.5, "time_off", "leave form", ANY)
