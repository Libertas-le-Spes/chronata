import unittest
from datetime import timedelta

from chronata.use_cases.questions.questions import Answers
from tests.fakes import Fixture, hours


def clocked(f: Fixture, came_in: str, left: str) -> int:
    f.at(f"2026-10-14T{came_in}:00")
    f.app.clocking.clock_in(None, None)
    f.at(f"2026-10-14T{left}:00")
    f.app.clocking.clock_out(None, None)
    return f.app.log.shifts()[-1].id


def set_up_hours() -> Fixture:
    f = Fixture("2026-10-14T07:00:00")
    f.app.setup.configure(hours("08:00", "17:00"), "Primary")
    return f


class WaivingTheEveningAfterComingInLate(unittest.TestCase):
    def setUp(self):
        self.f = set_up_hours()
        self.shift = clocked(self.f, "08:30", "19:00")
        self.outcome = self.f.app.waivers.waive([self.shift], "17:00", "19:00", "forgot to clock out")

    def test_only_the_time_after_the_lateness_is_made_up_is_waived(self):
        waiver = self.f.app.log.shifts()[0].breaks[0]
        self.assertEqual((f"{waiver.start:%H:%M}", f"{waiver.end:%H:%M}"), ("17:30", "19:00"))

    def test_the_late_start_stays_made_up(self):
        day = self.f.app.log.weeks_per_label()["Primary"][0].days[0]
        self.assertEqual(day.uncovered_lateness, timedelta())

    def test_no_overtime_is_left(self):
        day = self.f.app.log.weeks_per_label()["Primary"][0].days[0]
        self.assertEqual(day.overtime.earned, timedelta())

    def test_the_message_says_what_was_kept_and_why(self):
        self.assertIn("kept 17:00:00 to 17:30:00 (0:30), which makes up for coming in late", self.outcome.message)


class WaivingTheEveningAfterComingInOnTime(unittest.TestCase):
    def test_the_whole_stretch_is_waived(self):
        f = set_up_hours()
        shift = clocked(f, "08:00", "19:00")
        f.app.waivers.waive([shift], "17:00", "19:00", "forgot to clock out")
        waiver = f.app.log.shifts()[0].breaks[0]
        self.assertEqual((f"{waiver.start:%H:%M}", f"{waiver.end:%H:%M}"), ("17:00", "19:00"))


class WaivingOnlyTimeThatMakesUpTheLateness(unittest.TestCase):
    def setUp(self):
        self.f = set_up_hours()
        self.shift = clocked(self.f, "09:00", "17:30")
        self.outcome = self.f.app.waivers.waive([self.shift], "17:00", "17:30", "forgot to clock out")

    def test_nothing_is_waived(self):
        self.assertEqual(self.f.app.log.shifts()[0].breaks, [])

    def test_the_message_says_why_nothing_was_waived(self):
        self.assertEqual(self.outcome.message, "nothing waived: 17:00:00 to 17:30:00 makes up for coming in late, so it still counts")


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
        waiver = f.app.log.shifts()[-1].breaks[0]
        self.assertEqual((f"{waiver.start:%H:%M}", f"{waiver.end:%H:%M}"), ("18:00", "20:00"))


if __name__ == "__main__":
    unittest.main()
