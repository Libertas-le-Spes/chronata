import unittest
from datetime import timedelta

from chronata.use_cases.away.away_stretch import AwayStretch
from chronata.use_cases.questions.questions import Answers
from tests.fakes import Fixture, at, hours


class AwayFromThePc(unittest.TestCase):
    def start(self, moment: str, label: str | None = None, answers: Answers = Answers()) -> None:
        self.f = Fixture(moment)
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")
        self.f.app.labels.create("Secondary", Answers(no_set_hours=True))
        self.f.app.clocking.clock_in(None, None, label, answers)
        self.shift = self.f.app.log.shifts()[0].id

    def away_between(self, left: str, back: str) -> AwayStretch | None:
        self.f.at(left)
        self.f.app.away.began(600)
        self.f.at(back)
        self.f.app.away.ended()
        return self.asked_about()

    def asked_about(self) -> AwayStretch | None:
        away = self.f.app.away.to_ask_about()
        if away is None:
            return None
        return away.stretch


class WhenItIsAskedAbout(AwayFromThePc):
    def test_away_after_the_shift_is_asked_about_from_when_input_stopped(self):
        self.start("2026-10-14T08:00:00")
        stretch = self.away_between("2026-10-14T18:10:00", "2026-10-14T19:40:00")
        self.assertEqual(stretch, AwayStretch(self.shift, at("2026-10-14T18:00:00"), at("2026-10-14T19:40:00")))

    def test_away_that_ended_before_the_shift_did_is_not_asked_about(self):
        self.start("2026-10-14T08:00:00")
        self.assertIsNone(self.away_between("2026-10-14T14:10:00", "2026-10-14T16:30:00"))

    def test_away_that_runs_past_the_shift_end_is_asked_about_from_when_you_left(self):
        self.start("2026-10-14T08:00:00")
        self.assertEqual(self.away_between("2026-10-14T16:50:00", "2026-10-14T18:00:00").since, at("2026-10-14T16:40:00"))

    def test_still_away_when_clicking_counts_up_to_now(self):
        self.start("2026-10-14T08:00:00")
        self.f.at("2026-10-14T18:10:00")
        self.f.app.away.began(600)
        self.f.at("2026-10-14T19:00:00")
        self.assertEqual(self.asked_about().back, at("2026-10-14T19:00:00"))

    def test_on_a_day_off_any_time_away_is_asked_about(self):
        self.start("2026-10-17T09:00:00")
        self.assertIsNotNone(self.away_between("2026-10-17T10:10:00", "2026-10-17T10:40:00"))

    def test_on_a_label_without_set_hours_any_time_away_is_asked_about(self):
        self.start("2026-10-14T08:00:00", "Secondary", Answers(off_default=True))
        self.assertIsNotNone(self.away_between("2026-10-14T10:10:00", "2026-10-14T10:40:00"))

    def test_nothing_is_asked_about_without_being_away(self):
        self.start("2026-10-14T08:00:00")
        self.f.at("2026-10-14T19:00:00")
        self.assertIsNone(self.f.app.away.to_ask_about())


class HowItIsWorded(AwayFromThePc):
    def occasion(self) -> str:
        return self.f.app.away.to_ask_about().occasion

    def test_on_a_workday_it_says_past_the_end_of_your_shift(self):
        self.start("2026-10-14T08:00:00")
        self.away_between("2026-10-14T16:50:00", "2026-10-14T17:30:00")
        self.assertEqual(self.occasion(), "past the end of your shift")

    def test_on_a_day_off_it_says_so(self):
        self.start("2026-10-17T09:00:00")
        self.away_between("2026-10-17T10:10:00", "2026-10-17T10:40:00")
        self.assertEqual(self.occasion(), "on your day off")

    def test_on_a_label_without_set_hours_it_says_so(self):
        self.start("2026-10-14T08:00:00", "Secondary", Answers(off_default=True))
        self.away_between("2026-10-14T10:10:00", "2026-10-14T10:40:00")
        self.assertEqual(self.occasion(), "on a label without set hours")


class WhenYouLeftAfterClockingIn(AwayFromThePc):
    def test_input_stopping_after_the_clock_in_counts_as_leaving_after_it(self):
        self.start("2026-10-14T08:00:00")
        self.away_between("2026-10-14T18:10:00", "2026-10-14T18:40:00")
        self.assertTrue(self.f.app.away.to_ask_about().left_after_clocking_in)

    def test_input_stopping_before_a_fresh_clock_in_does_not(self):
        self.start("2026-10-14T18:05:00", answers=Answers(overtime=True))
        self.away_between("2026-10-14T18:10:00", "2026-10-14T18:40:00")
        self.assertFalse(self.f.app.away.to_ask_about().left_after_clocking_in)


class WhatIsKept(AwayFromThePc):
    def test_being_away_again_without_a_noted_return_starts_afresh_because_you_must_have_come_back(self):
        self.start("2026-10-14T08:00:00")
        self.f.at("2026-10-14T11:00:00")
        self.f.app.away.began(600)
        self.f.at("2026-10-14T18:10:00")
        self.f.app.away.began(600)
        self.f.at("2026-10-14T18:40:00")
        self.assertEqual(self.asked_about().since, at("2026-10-14T18:00:00"))

    def test_a_new_time_away_after_coming_back_replaces_the_last(self):
        self.start("2026-10-14T08:00:00")
        self.away_between("2026-10-14T18:10:00", "2026-10-14T18:30:00")
        self.assertEqual(self.away_between("2026-10-14T19:10:00", "2026-10-14T19:40:00").since, at("2026-10-14T19:00:00"))

    def test_coming_back_twice_keeps_the_first_return(self):
        self.start("2026-10-14T08:00:00")
        self.away_between("2026-10-14T18:10:00", "2026-10-14T19:00:00")
        self.f.at("2026-10-14T19:30:00")
        self.f.app.away.ended()
        self.assertEqual(self.asked_about().back, at("2026-10-14T19:00:00"))

    def test_the_time_away_never_starts_before_the_last_clock_in(self):
        self.start("2026-10-14T18:05:00", answers=Answers(overtime=True))
        self.assertEqual(self.away_between("2026-10-14T18:10:00", "2026-10-14T18:40:00").since, at("2026-10-14T18:05:00"))

    def test_being_away_while_clocked_out_notes_nothing(self):
        self.start("2026-10-14T08:00:00")
        self.f.at("2026-10-14T17:30:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T18:10:00")
        self.f.app.away.began(600)
        self.f.at("2026-10-14T18:40:00")
        self.f.app.clocking.clock_in(None, None, None, Answers(overtime=True))
        self.f.at("2026-10-14T19:00:00")
        self.assertIsNone(self.f.app.away.to_ask_about())

    def test_time_away_on_an_earlier_shift_is_not_asked_about(self):
        self.start("2026-10-14T08:00:00")
        self.f.at("2026-10-14T18:10:00")
        self.f.app.away.began(600)
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T18:30:00")
        self.f.app.clocking.clock_in(None, None, None, Answers(overtime=True))
        self.f.at("2026-10-14T19:30:00")
        self.assertIsNone(self.f.app.away.to_ask_about())

    def test_settling_it_forgets_the_time_away(self):
        self.start("2026-10-14T08:00:00")
        self.away_between("2026-10-14T18:10:00", "2026-10-14T19:00:00")
        self.f.app.away.settled()
        self.assertIsNone(self.f.app.away.to_ask_about())

    def test_under_ten_minutes_away_is_not_asked_about(self):
        self.start("2026-10-14T08:00:00")
        self.f.at("2026-10-14T18:05:00")
        self.f.app.away.began(0)
        self.f.at("2026-10-14T18:14:00")
        self.f.app.away.ended()
        self.assertIsNone(self.f.app.away.to_ask_about())


if __name__ == "__main__":
    unittest.main()
