import unittest

from chronata.use_cases.questions.questions import Answers
from tests.use_cases.waivers.waiver_days import clocked, set_up_hours, waived_spans


class WaivingTheEveningAfterComingInOnTime(unittest.TestCase):
    def setUp(self):
        self.f = set_up_hours()
        shift = clocked(self.f, "08:00", "19:00")
        self.outcome = self.f.app.waivers.waive([shift], "17:00", "19:00", "forgot to clock out")

    def test_the_whole_stretch_is_waived(self):
        self.assertEqual(waived_spans(self.f), [("17:00", "19:00")])

    def test_the_message_keeps_nothing(self):
        self.assertEqual(self.outcome.message, "waived 2026-10-14 17:00:00 to 19:00:00, 2:00 no longer counted")


class WaivingAnEveningAnsweredAsOvertime(unittest.TestCase):
    def test_the_whole_stretch_is_waived_because_overtime_never_makes_up_lateness(self):
        f = set_up_hours()
        clocked(f, "08:30", "17:00")
        f.at("2026-10-14T18:00:00")
        f.app.clocking.clock_in(None, None, None, Answers(overtime=True))
        f.at("2026-10-14T20:00:00")
        f.app.clocking.clock_out(None, None)
        evening = f.app.log.shifts()[-1].id
        f.app.waivers.waive([evening], "18:00", "20:00", "forgot to clock out")
        self.assertEqual(waived_spans(f), [("18:00", "20:00")])


class WaivingWhileStillClockedIn(unittest.TestCase):
    def test_the_whole_stretch_is_waived_because_later_work_can_still_make_up_the_lateness(self):
        f = set_up_hours()
        f.at("2026-10-14T08:30:00")
        f.app.clocking.clock_in(None, None)
        f.at("2026-10-14T19:00:00")
        f.app.waivers.waive([f.app.log.shifts()[0].id], "17:00", "19:00", "away from the PC")
        self.assertEqual(waived_spans(f), [("17:00", "19:00")])


class WaivingAStretchInsideTheShift(unittest.TestCase):
    def test_the_whole_stretch_is_waived_because_only_time_after_the_shift_is_kept(self):
        f = set_up_hours()
        shift = clocked(f, "08:30", "17:30")
        f.app.waivers.waive([shift], "12:00", "12:30", "long lunch")
        self.assertEqual(waived_spans(f), [("12:00", "12:30")])


class WaivingTheEveningOfADayShortByMoreThanTheLateness(unittest.TestCase):
    def test_the_whole_stretch_is_waived_because_keeping_it_would_not_cover_the_lateness(self):
        f = set_up_hours()
        clocked(f, "08:30", "12:00")
        evening = clocked(f, "14:00", "18:00")
        f.app.waivers.waive([evening], "17:00", "18:00", "forgot to clock out")
        self.assertEqual(waived_spans(f), [("17:00", "18:00")])


if __name__ == "__main__":
    unittest.main()
