import unittest

from chronata.use_cases.questions import Answers, LabelNeedsHours
from tests.fakes import Fixture


class RecordingCompensation(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T17:00:00")
        self.f.app.setup.configure("12:00 for 60 min", "08:00 to 17:00", "Northwind")
        self.f.app.labels.create("Acme", Answers(no_set_hours=True))

    def recorded(self) -> list[dict]:
        return [entry.data for entry in self.f.app.log.record.entries() if entry.kind == "compensation"]

    def test_it_is_recorded_against_the_label_it_was_for(self):
        outcome = self.f.app.compensations.record("acme", "2026-10-01", "2026-10-31", 2, False, "invoice 7")
        self.assertEqual(self.recorded()[0]["label"], "Acme")
        self.assertEqual(outcome.message, "recorded 2h of Acme overtime paid for 2026-10-01 to 2026-10-31")

    def test_leaving_the_label_out_means_the_default(self):
        self.f.app.compensations.record("", "2026-10-01", "2026-10-31", 0, False, None)
        self.assertEqual(self.recorded()[0]["label"], "Northwind")

    def test_a_label_that_does_not_exist_is_refused(self):
        with self.assertRaises(LabelNeedsHours):
            self.f.app.compensations.record("Initech", "2026-10-01", "2026-10-31", 2, False, None)
        self.assertEqual(self.recorded(), [])


if __name__ == "__main__":
    unittest.main()
