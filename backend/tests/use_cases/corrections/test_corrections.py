import unittest

from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions.questions import Answers
from tests.fakes import Fixture, at


class CorrectingADay(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-15T18:00:00")
        self.f.app.setup.configure("12:00 for 60 min", "08:30 to 17:30", "Northwind")
        self.f.app.corrections.add("2026-10-15", "08:41", "09:04", "from when the PC came on", None, "Northwind")
        self.f.app.corrections.add("2026-10-15", "09:04", "17:00", "forgot to clock", None, "Northwind")
        self.ids = [shift.id for shift in self.f.app.log.shifts()]

    def spans(self) -> list[tuple]:
        return [(shift.start, shift.end, shift.voided) for shift in self.f.app.log.shifts()]

    def test_the_day_start_moves_the_first_entry_and_the_day_end_the_last(self):
        outcome = self.f.app.corrections.correct(self.ids, "08:30", "17:30", "early meeting")
        self.assertEqual(self.spans(), [(at("2026-10-15T08:30:00"), at("2026-10-15T09:04:00"), False),
                                        (at("2026-10-15T09:04:00"), at("2026-10-15T17:30:00"), False)])
        self.assertTrue(outcome.message.startswith("corrected shifts"))

    def test_only_the_entry_whose_time_changes_gets_a_correction(self):
        self.f.app.corrections.correct(self.ids, "08:30", None, "early meeting")
        self.assertEqual([len(shift.corrections) for shift in self.f.app.log.shifts()], [1, 0])

    def test_unchanged_times_are_refused(self):
        with self.assertRaisesRegex(UserError, "already the times"):
            self.f.app.corrections.correct(self.ids, "08:41", "17:00", "nothing")

    def test_marking_the_day_a_mistake_stops_all_of_it_counting(self):
        outcome = self.f.app.corrections.mark_mistake(self.ids, "wrong day")
        self.assertEqual([voided for _, _, voided in self.spans()], [True, True])
        self.assertEqual(outcome.message, f"marked shifts {self.ids[0]}, {self.ids[1]} as a mistake")

    def test_a_mistake_needs_a_reason(self):
        with self.assertRaises(UserError):
            self.f.app.corrections.mark_mistake(self.ids, " ")

    def test_labelling_the_day_labels_every_entry(self):
        self.f.app.labels.create("Acme", Answers(no_set_hours=True))
        self.f.app.labels.label_shifts(self.ids, "Acme")
        self.assertEqual([shift.label for shift in self.f.app.log.shifts()], ["Acme", "Acme"])
