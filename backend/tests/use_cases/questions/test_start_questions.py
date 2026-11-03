import unittest

from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions.questions import AfterShift, Answers, LateOrOtherProject
from tests.fakes import Fixture, hours


class StartingOnASecondLabel(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T07:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")
        self.f.app.labels.create("Secondary", hours("10:00", "17:00", new_label=True))
        self.f.app.clocking.clock_in(None, None, "Primary")
        self.f.at("2026-10-14T09:30:00")
        self.f.app.clocking.clock_out(None, None)

    def clock_in_on_secondary(self, moment: str, answers: Answers = Answers()) -> dict:
        self.f.at(moment)
        self.f.app.clocking.clock_in(None, None, "Secondary", Answers(off_default=True, late=answers.late, other_project=answers.other_project))
        return self.f.app.log.record.entries()[-1].data

    def test_after_its_shift_start_asks_whether_you_are_late_or_on_another_project(self):
        with self.assertRaises(LateOrOtherProject):
            self.clock_in_on_secondary("2026-10-14T10:40:00")

    def test_answering_late_is_kept_with_the_clock_in(self):
        self.assertIs(self.clock_in_on_secondary("2026-10-14T10:40:00", Answers(late=True))["late"], True)

    def test_answering_another_project_is_kept_with_the_clock_in(self):
        self.assertIs(self.clock_in_on_secondary("2026-10-14T10:40:00", Answers(other_project=True))["late"], False)

    def test_before_its_shift_start_nothing_is_asked(self):
        self.f.app.clocking.clock_in(None, None, "Secondary", Answers(off_default=True))
        self.assertNotIn("late", self.f.app.log.record.entries()[-1].data)

    def test_clocking_in_on_a_label_already_worked_today_asks_nothing(self):
        self.f.at("2026-10-14T09:45:00")
        self.f.app.clocking.clock_in(None, None, "Secondary", Answers(off_default=True))
        self.f.at("2026-10-14T10:20:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T10:40:00")
        self.f.app.clocking.clock_in(None, None, "Primary", Answers(late=True))
        self.assertEqual(self.f.app.log.record.entries()[-1].kind, "clock_in")
        self.assertNotIn("late", self.f.app.log.record.entries()[-1].data)

    def test_after_its_shift_has_ended_nothing_is_asked(self):
        self.f.at("2026-10-14T17:30:00")
        self.f.app.clocking.clock_in(None, None, "Secondary", Answers(off_default=True, late=True))
        self.assertNotIn("late", self.f.app.log.record.entries()[-1].data)

    def test_both_answers_at_once_are_refused(self):
        with self.assertRaises(UserError):
            self.clock_in_on_secondary("2026-10-14T10:40:00", Answers(late=True, other_project=True))


class AnEarlierShiftWithNoLabel(unittest.TestCase):
    def test_counts_as_the_default_label_so_nothing_is_asked(self):
        self.f = Fixture("2026-10-14T07:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")
        self.f.app.clocking.clock_in(None, None, "", Answers(off_default=True))
        self.f.at("2026-10-14T09:30:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T10:40:00")
        self.f.app.clocking.clock_in(None, None, "Primary")
        self.assertEqual(self.f.app.log.record.entries()[-1].kind, "clock_in")


class AnswersNobodyAskedFor(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T09:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")

    def test_overtime_given_during_the_shift_is_not_kept(self):
        self.f.app.clocking.clock_in(None, None, None, Answers(overtime=True))
        self.assertNotIn("overtime_after_shift", self.f.app.log.record.entries()[-1].data)

    def test_late_given_on_the_first_label_of_the_day_is_not_kept(self):
        self.f.app.clocking.clock_in(None, None, None, Answers(late=True))
        self.assertNotIn("late", self.f.app.log.record.entries()[-1].data)


class FirstClockInAfterTheShift(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T18:30:00")
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")

    def test_on_a_workday_it_asks_whether_this_is_overtime(self):
        with self.assertRaises(AfterShift):
            self.f.app.clocking.clock_in(None, None)

    def test_answering_overtime_is_kept_with_the_clock_in(self):
        self.f.app.clocking.clock_in(None, None, None, Answers(overtime=True))
        self.assertEqual(self.f.app.log.record.entries()[-1].data["overtime_after_shift"], True)

    def test_answering_normal_hours_is_kept_with_the_clock_in(self):
        self.f.app.clocking.clock_in(None, None, None, Answers(normal_hours=True))
        self.assertEqual(self.f.app.log.record.entries()[-1].data["overtime_after_shift"], False)

    def test_on_a_day_off_nothing_is_asked(self):
        self.f.at("2026-10-17T18:30:00")
        self.f.app.clocking.clock_in(None, None)
        self.assertNotIn("overtime_after_shift", self.f.app.log.record.entries()[-1].data)

    def test_after_working_earlier_that_day_nothing_is_asked(self):
        self.f.at("2026-10-14T08:00:00")
        self.f.app.clocking.clock_in(None, None)
        self.f.at("2026-10-14T12:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T18:30:00")
        self.f.app.clocking.clock_in(None, None, "Primary")
        self.assertNotIn("overtime_after_shift", self.f.app.log.record.entries()[-1].data)

    def test_both_answers_at_once_are_refused(self):
        with self.assertRaises(UserError):
            self.f.app.clocking.clock_in(None, None, None, Answers(overtime=True, normal_hours=True))


class AddingAMissedShift(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-15T09:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")

    def test_an_evening_added_later_asks_whether_it_was_overtime(self):
        with self.assertRaises(AfterShift):
            self.f.app.corrections.add("2026-10-14", "18:00", "20:00", "forgot to clock in", None, "Primary")

    def test_the_answer_is_kept_with_the_added_shift(self):
        self.f.app.corrections.add("2026-10-14", "18:00", "20:00", "forgot to clock in", None, "Primary", Answers(overtime=True))
        self.assertIs(self.f.app.log.record.entries()[-1].data["overtime_after_shift"], True)


if __name__ == "__main__":
    unittest.main()
