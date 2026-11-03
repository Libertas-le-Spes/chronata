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

    def test_after_its_shift_has_ended_it_asks_whether_this_is_overtime(self):
        self.f.at("2026-10-14T17:30:00")
        with self.assertRaises(AfterShift):
            self.f.app.clocking.clock_in(None, None, "Secondary", Answers(off_default=True, late=True))

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


class MovingAnAnsweredShift(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T07:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")
        self.f.app.labels.create("Secondary", hours("10:00", "17:00", new_label=True))
        self.f.app.labels.create("Tertiary", hours("08:00", "17:00", new_label=True))
        self.f.app.clocking.clock_in(None, None, "Primary")
        self.f.at("2026-10-14T09:30:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T10:40:00")
        self.f.app.clocking.clock_in(None, None, "Secondary", Answers(off_default=True, late=True))
        self.f.at("2026-10-14T12:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.answered = self.f.app.log.shifts()[-1].id

    def answer(self):
        return self.f.app.log.shift(self.answered).start_answer

    def counted(self) -> str:
        return self.f.app.log.hours.counted_under(self.f.app.log.shift(self.answered).label)

    def test_merging_into_an_existing_label_leaves_the_answer_behind(self):
        self.f.app.clocking.clock_in(None, None, "Tertiary", Answers(off_default=True, other_project=True))
        self.f.at("2026-10-14T12:20:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.app.labels.rename("Secondary", "Tertiary", Answers())
        self.assertFalse(self.answer().said_late_for(self.counted()))

    def test_correcting_only_the_end_keeps_a_later_pieces_answer(self):
        self.f.at("2026-10-14T13:00:00")
        first = self.f.app.log.shifts()[0].id
        self.f.app.corrections.correct([first, self.answered], None, "12:30", "left a little later")
        self.assertTrue(self.answer().said_late_for(self.counted()))

    def test_renaming_the_label_keeps_the_answer(self):
        self.f.app.labels.rename("Secondary", "Evenings", Answers())
        self.assertTrue(self.answer().said_late_for(self.counted()))

    def test_moving_the_shift_to_another_label_clears_the_answer(self):
        self.f.app.labels.label_shifts([self.answered], "Tertiary", Answers())
        self.assertFalse(self.answer().said_late_for(self.counted()))

    def test_correcting_only_the_end_after_moving_it_brings_no_answer_back(self):
        self.f.app.labels.label_shifts([self.answered], "Tertiary", Answers())
        self.f.at("2026-10-14T13:00:00")
        self.f.app.corrections.correct([self.answered], None, "12:30", "left a little later")
        self.assertFalse(self.answer().said_late_for(self.counted()))

    def test_correcting_only_a_later_piece_keeps_the_first_pieces_answer_without_asking(self):
        self.f.at("2026-10-14T12:15:00")
        self.f.app.clocking.clock_in(None, None, "Primary")
        self.f.at("2026-10-14T12:30:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T12:45:00")
        self.f.app.clocking.clock_in(None, None, "Secondary", Answers(off_default=True))
        self.f.at("2026-10-14T13:30:00")
        self.f.app.clocking.clock_out(None, None)
        later_piece = self.f.app.log.shifts()[-1].id
        self.f.at("2026-10-14T14:00:00")
        self.f.app.corrections.correct([self.answered, later_piece], None, "13:45", "left a little later")
        self.assertTrue(self.answer().said_late_for(self.counted()))


class AnUnlabelledShiftAfterTheShift(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T18:30:00")
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")
        self.f.app.labels.create("Tertiary", hours("08:00", "17:00", new_label=True))
        self.f.app.clocking.clock_in(None, None, "", Answers(off_default=True, overtime=True))
        self.f.at("2026-10-14T20:30:00")
        self.f.app.clocking.clock_out(None, None)
        self.shift = self.f.app.log.shifts()[0].id

    def overtime_under(self, label: str):
        day = self.f.app.log.weeks_per_label()[label][0].days[0]
        return day.overtime.earned, day.worked

    def test_answering_overtime_counts_it_as_overtime_for_the_default_label(self):
        earned, worked = self.overtime_under("Primary")
        self.assertEqual(earned, worked)

    def test_giving_it_the_default_label_by_name_keeps_the_answer(self):
        self.f.app.labels.label_shifts([self.shift], "Primary", Answers())
        earned, worked = self.overtime_under("Primary")
        self.assertEqual(earned, worked)

    def test_renaming_the_default_label_keeps_the_answer(self):
        self.f.app.labels.rename("Primary", "Main", Answers())
        earned, worked = self.overtime_under("Main")
        self.assertEqual(earned, worked)

    def test_making_another_label_the_default_leaves_the_answer_behind(self):
        self.f.app.labels.set_default("Tertiary", Answers())
        earned, worked = self.overtime_under("Tertiary")
        self.assertNotEqual(earned, worked)


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


class ClockingInAfterTheShift(unittest.TestCase):
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

    def work_the_morning(self):
        self.f.at("2026-10-14T08:00:00")
        self.f.app.clocking.clock_in(None, None)
        self.f.at("2026-10-14T12:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T18:30:00")

    def test_after_working_earlier_that_day_it_still_asks(self):
        self.work_the_morning()
        with self.assertRaises(AfterShift):
            self.f.app.clocking.clock_in(None, None, "Primary")

    def test_answering_overtime_after_working_earlier_starts_a_shift_of_its_own(self):
        self.work_the_morning()
        self.f.app.clocking.clock_in(None, None, "Primary", Answers(overtime=True))
        entry = self.f.app.log.record.entries()[-1]
        self.assertEqual((entry.kind, entry.data["overtime_after_shift"]), ("clock_in", True))

    def test_answering_normal_hours_after_working_earlier_carries_on_the_days_shift(self):
        self.work_the_morning()
        self.f.app.clocking.clock_in(None, None, "Primary", Answers(normal_hours=True))
        self.assertEqual(self.f.app.log.record.entries()[-1].kind, "clock_resumed")

    def test_answering_normal_hours_after_an_overtime_evening_starts_a_shift_of_its_own(self):
        self.work_the_morning()
        self.f.app.clocking.clock_in(None, None, "Primary", Answers(overtime=True))
        self.f.at("2026-10-14T19:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T19:30:00")
        self.f.app.clocking.clock_in(None, None, "Primary", Answers(normal_hours=True))
        entry = self.f.app.log.record.entries()[-1]
        self.assertEqual((entry.kind, entry.data["overtime_after_shift"]), ("clock_in", False))

    def test_coming_back_before_the_shift_ends_carries_on_without_asking(self):
        self.work_the_morning()
        self.f.at("2026-10-14T13:00:00")
        self.f.app.clocking.clock_in(None, None, "Primary")
        self.assertEqual(self.f.app.log.record.entries()[-1].kind, "clock_resumed")

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


class CorrectingAShift(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:30:00")
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")
        self.f.app.clocking.clock_in(None, None)
        self.f.at("2026-10-14T21:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.shift = self.f.app.log.shifts()[0].id

    def test_moving_the_start_after_the_shift_asks_whether_it_was_overtime(self):
        with self.assertRaises(AfterShift):
            self.f.app.corrections.correct([self.shift], "18:30", "20:30", "clocked in by mistake in the morning")

    def test_the_answer_is_kept_with_the_correction(self):
        self.f.app.corrections.correct([self.shift], "18:30", "20:30", "clocked in by mistake in the morning", Answers(overtime=True))
        self.assertTrue(self.f.app.log.shifts()[0].start_answer.said_overtime_for("Primary"))

    def test_moving_the_start_back_into_the_shift_clears_the_earlier_answer(self):
        self.f.app.corrections.correct([self.shift], "18:30", "20:30", "clocked in by mistake in the morning", Answers(overtime=True))
        self.f.app.corrections.correct([self.shift], "08:30", "20:30", "it was the morning after all")
        self.assertFalse(self.f.app.log.shifts()[0].start_answer.said_overtime_for("Primary"))

    def test_correcting_only_the_end_keeps_the_answer_without_asking_again(self):
        self.f.app.corrections.correct([self.shift], "18:30", "20:30", "clocked in by mistake in the morning", Answers(overtime=True))
        self.f.app.corrections.correct([self.shift], None, "20:45", "left a little later")
        self.assertTrue(self.f.app.log.shifts()[0].start_answer.said_overtime_for("Primary"))


if __name__ == "__main__":
    unittest.main()
