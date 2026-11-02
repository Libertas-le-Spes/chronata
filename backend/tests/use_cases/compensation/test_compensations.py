import unittest

from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions.questions import Answers, LabelNeedsHours
from tests.fakes import Fixture, hours


class RecordingCompensation(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T17:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00", "12:00", "60"), "Primary")
        self.f.app.labels.create("Secondary", Answers(no_set_hours=True))

    def recorded(self) -> list[dict]:
        return [entry.data for entry in self.f.app.log.record.entries() if entry.kind == "compensation"]

    def test_it_is_recorded_against_the_label_it_was_for(self):
        outcome = self.f.app.compensations.record("secondary", "2026-10-01", "2026-10-31", 2, "paid", "invoice 7")
        self.assertEqual(self.recorded()[0]["label"], "Secondary")
        self.assertEqual(outcome.message, "recorded 2h of Secondary overtime paid for 2026-10-01 to 2026-10-31")

    def test_leaving_the_label_out_means_the_default(self):
        self.f.app.compensations.record("", "2026-10-01", "2026-10-31", 0, "paid", None)
        self.assertEqual(self.recorded()[0]["label"], "Primary")

    def test_a_label_that_does_not_exist_is_refused(self):
        with self.assertRaises(LabelNeedsHours):
            self.f.app.compensations.record("Missing", "2026-10-01", "2026-10-31", 2, "paid", None)
        self.assertEqual(self.recorded(), [])

    def test_time_off_is_recorded_as_time_off(self):
        outcome = self.f.app.compensations.record("", "2026-10-01", "2026-10-31", 1, "time_off", None)
        self.assertEqual(self.recorded()[0]["kind"], "time_off")
        self.assertEqual(outcome.message, "recorded 1h of Primary overtime given as time off for 2026-10-01 to 2026-10-31")

    def test_a_way_of_compensating_it_does_not_know_is_refused(self):
        with self.assertRaises(UserError):
            self.f.app.compensations.record("", "2026-10-01", "2026-10-31", 1, "bonus", None)
        self.assertEqual(self.recorded(), [])


if __name__ == "__main__":
    unittest.main()
