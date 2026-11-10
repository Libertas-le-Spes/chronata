import unittest
from datetime import timedelta

from tests.use_cases.waivers.waiver_days import clocked, set_up_hours, waived_spans


class WaivingTheEveningAfterComingInLate(unittest.TestCase):
    def setUp(self):
        self.f = set_up_hours()
        self.shift = clocked(self.f, "08:30", "19:00")
        self.outcome = self.f.app.waivers.waive([self.shift], "17:00", "19:00", "forgot to clock out")

    def test_only_the_time_after_the_lateness_is_made_up_is_waived(self):
        self.assertEqual(waived_spans(self.f), [("17:30", "19:00")])

    def test_the_late_start_stays_made_up(self):
        day = self.f.app.log.weeks_per_label()["Primary"][0].days[0]
        self.assertEqual(day.uncovered_lateness, timedelta())

    def test_no_overtime_is_left(self):
        day = self.f.app.log.weeks_per_label()["Primary"][0].days[0]
        self.assertEqual(day.overtime.earned, timedelta())

    def test_the_message_says_what_was_kept_and_why(self):
        self.assertIn("kept 17:00:00 to 17:30:00 (0:30), which makes up for coming in late", self.outcome.message)


class WaivingOnlyTimeThatMakesUpTheLateness(unittest.TestCase):
    def setUp(self):
        self.f = set_up_hours()
        self.shift = clocked(self.f, "09:00", "17:30")
        self.outcome = self.f.app.waivers.waive([self.shift], "17:00", "17:30", "forgot to clock out")

    def test_nothing_is_waived(self):
        self.assertEqual(self.f.app.log.shifts()[0].breaks, [])

    def test_the_message_says_why_nothing_was_waived(self):
        self.assertEqual(self.outcome.message, "nothing waived: 17:00:00 to 17:30:00 makes up for coming in late, so it still counts")


class WaivingAStretchThatStartsBeforeTheShiftEnds(unittest.TestCase):
    def test_the_time_before_the_shift_end_is_waived_and_the_make_up_after_it_is_kept(self):
        f = set_up_hours()
        shift = clocked(f, "08:30", "19:00")
        f.app.waivers.waive([shift], "16:30", "19:00", "forgot to clock out")
        self.assertEqual(waived_spans(f), [("16:30", "17:00"), ("18:00", "19:00")])


class WaivingTheEveningAfterABreakInTheDay(unittest.TestCase):
    def setUp(self):
        self.f = set_up_hours()
        clocked(self.f, "08:30", "12:00")
        evening = clocked(self.f, "13:00", "19:00")
        self.f.app.waivers.waive([evening], "17:00", "19:00", "forgot to clock out")

    def test_as_much_is_kept_as_the_day_needs_to_cover_the_late_start(self):
        self.assertEqual(waived_spans(self.f), [("18:30", "19:00")])

    def test_the_late_start_stays_made_up(self):
        day = self.f.app.log.weeks_per_label()["Primary"][0].days[0]
        self.assertEqual(day.uncovered_lateness, timedelta())


if __name__ == "__main__":
    unittest.main()
