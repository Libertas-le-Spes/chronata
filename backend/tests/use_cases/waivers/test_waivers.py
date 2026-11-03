import unittest
from datetime import timedelta

from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions.questions import Answers
from tests.fakes import Fixture, hours


def day_left_running(f: Fixture) -> int:
    f.app.setup.configure(hours("08:00", "17:00", "12:00", "60"), "Primary")
    f.app.clocking.clock_in(None, None)
    f.at("2026-10-14T23:10:00")
    f.app.clocking.clock_out(None, None)
    return f.app.log.shifts()[0].id


class WaivingTheEveningAfterForgettingToClockOut(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.shift = day_left_running(self.f)

    def overtime(self) -> timedelta:
        return self.f.app.log.weeks_per_label()["Primary"][0].days[0].overtime.earned

    def test_the_waived_stretch_stops_counting_as_overtime(self):
        before = self.overtime()
        self.f.app.waivers.waive([self.shift], "17:30", "23:10", "forgot to clock out")
        self.assertEqual(before - self.overtime(), timedelta(hours=5, minutes=40))

    def test_the_clocked_times_stay_on_record(self):
        self.f.app.waivers.waive([self.shift], "17:30", "23:10", "forgot to clock out")
        shift = self.f.app.log.shifts()[0]
        self.assertEqual((f"{shift.start:%H:%M}", f"{shift.end:%H:%M}"), ("08:00", "23:10"))

    def test_the_day_shows_what_was_waived_and_why(self):
        self.f.app.waivers.waive([self.shift], "17:30", "23:10", "forgot to clock out")
        waived = self.f.app.log.shifts()[0].happenings[-1]
        self.assertEqual((waived.what, waived.detail), ("Waived", "17:30:00 – 23:10:00 · not counted · “forgot to clock out”"))

    def test_counting_it_again_brings_the_overtime_back(self):
        before = self.overtime()
        self.f.app.waivers.waive([self.shift], "17:30", "23:10", "forgot to clock out")
        start = self.f.app.log.shifts()[0].breaks[0].start.isoformat()
        self.f.app.waivers.withdraw(self.shift, start, "I was working after all")
        self.assertEqual(self.overtime(), before)

    def test_two_stretches_of_one_shift_can_each_be_waived(self):
        before = self.overtime()
        self.f.app.waivers.waive([self.shift], "21:00", "23:10", "forgot to clock out")
        self.f.app.waivers.waive([self.shift], "18:00", "19:00", "dinner")
        self.assertEqual(before - self.overtime(), timedelta(hours=3, minutes=10))


class WhatCannotBeWaived(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.shift = day_left_running(self.f)

    def test_a_stretch_without_a_reason(self):
        with self.assertRaisesRegex(UserError, "reason"):
            self.f.app.waivers.waive([self.shift], "17:30", "23:10", " ")

    def test_a_stretch_reaching_past_the_clock_out(self):
        self.f.at("2026-10-15T08:00:00")
        with self.assertRaisesRegex(UserError, "not inside one clocked shift"):
            self.f.app.waivers.waive([self.shift], "22:00", "23:30", "forgot to clock out")

    def test_a_stretch_starting_before_the_clock_in(self):
        with self.assertRaisesRegex(UserError, "not inside one clocked shift"):
            self.f.app.waivers.waive([self.shift], "07:30", "09:00", "not working yet")

    def test_a_stretch_in_the_future(self):
        self.f.at("2026-10-14T23:20:00")
        self.f.app.clocking.clock_in(None, None, None, Answers(overtime=True))
        with self.assertRaisesRegex(UserError, "future"):
            self.f.app.waivers.waive([self.shift], "23:15", "23:40", "not yet")

    def test_a_stretch_overlapping_one_already_waived(self):
        self.f.app.waivers.waive([self.shift], "17:30", "20:00", "forgot to clock out")
        with self.assertRaisesRegex(UserError, "overlaps"):
            self.f.app.waivers.waive([self.shift], "19:00", "21:00", "forgot to clock out")

    def test_a_stretch_of_a_shift_marked_as_a_mistake(self):
        self.f.app.corrections.mark_mistake([self.shift], "wrong day")
        with self.assertRaisesRegex(UserError, "not inside one clocked shift"):
            self.f.app.waivers.waive([self.shift], "17:30", "23:10", "forgot to clock out")

    def test_counting_again_a_waiver_that_is_not_there(self):
        with self.assertRaisesRegex(UserError, "no waiver"):
            self.f.app.waivers.withdraw(self.shift, "2026-10-14T17:30:00+02:00", "mistake")

    def test_counting_again_without_a_reason(self):
        self.f.app.waivers.waive([self.shift], "17:30", "23:10", "forgot to clock out")
        start = self.f.app.log.shifts()[0].breaks[0].start.isoformat()
        with self.assertRaisesRegex(UserError, "reason"):
            self.f.app.waivers.withdraw(self.shift, start, "")


class WaivingWhileStillClockedIn(unittest.TestCase):
    def test_a_stretch_up_to_now_can_be_waived(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00", "12:00", "60"), "Primary")
        self.f.app.clocking.clock_in(None, None)
        self.f.at("2026-10-14T19:00:00")
        self.f.app.waivers.waive([self.f.app.log.shifts()[0].id], "17:40", "19:00", "away from the desk")
        self.assertEqual(self.f.app.log.shifts()[0].worked(self.f.now), timedelta(hours=9, minutes=40))


if __name__ == "__main__":
    unittest.main()
