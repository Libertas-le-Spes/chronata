import unittest

from chronata.timekeeping.pc_sessions import Boot
from chronata.use_cases.reminders import Reminders
from tests.fakes import Fixture, at


class Lunch(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:30:00")
        self.f.app.setup.configure("12:00 for 60 min", "08:30 to 17:30")
        self.f.app.clocking.clock_in(None, None)
        self.reminders = Reminders(self.f.app.log, self.f.app.clocking, self.f.app.pc, self.f.desktop, "http://page/")

    def test_at_lunch_time_you_are_asked_and_ignoring_it_keeps_you_working(self):
        self.f.at("2026-10-14T12:00:30")
        self.reminders.tick()
        self.reminders.tick()
        self.assertEqual([summary for summary, _ in self.f.desktop.notices], ["Lunch time"])
        self.assertTrue(self.f.app.log.shifts()[0].end is None)

    def test_clocking_out_for_lunch_then_being_asked_back(self):
        self.f.at("2026-10-14T12:00:30")
        self.reminders.tick()
        self.f.desktop.click("Lunch time")
        self.assertIsNotNone(self.f.app.log.shifts()[0].end)
        self.f.at("2026-10-14T13:00:30")
        self.reminders.tick()
        self.f.desktop.click("Lunch is over")
        self.assertIsNone(self.f.app.log.shifts()[0].end)
        self.assertEqual(len(self.f.app.log.shifts()), 1)


class NotClockedIn(unittest.TestCase):
    def test_at_the_weekend_the_reminder_asks_whether_you_are_working(self):
        f = Fixture("2026-10-17T09:15:00")
        Reminders(f.app.log, f.app.clocking, f.app.pc, f.desktop, "http://page/").tick()
        self.assertEqual(f.desktop.notices[0][0], "It's Saturday. Working today?")

    def test_on_a_workday_it_reminds_twice_at_most(self):
        f = Fixture("2026-10-14T08:40:00")
        reminders = Reminders(f.app.log, f.app.clocking, f.app.pc, f.desktop, "http://page/")
        for moment in ("08:40", "09:00", "09:41", "10:50"):
            f.at(f"2026-10-14T{moment}:00")
            reminders.tick()
        self.assertEqual([summary for summary, _ in f.desktop.notices], ["Not clocked in", "Not clocked in"])

    def test_clocking_in_from_the_reminder_uses_the_default_label(self):
        f = Fixture("2026-10-14T08:40:00")
        f.app.setup.configure("12:00 for 60 min", "08:00 to 17:00", "Northwind")
        Reminders(f.app.log, f.app.clocking, f.app.pc, f.desktop, "http://page/").tick()
        f.desktop.click("Not clocked in")
        self.assertEqual(f.app.log.shifts()[0].label, "Northwind")


class PcOffPrompt(unittest.TestCase):
    def test_logging_in_after_the_pc_was_off_mid_shift_asks_why(self):
        f = Fixture("2026-10-14T08:31:00")
        f.power.boot_list = [Boot("morning", at("2026-10-14T08:30:00"), at("2026-10-14T08:31:00"), True)]
        f.power.booted = "morning"
        f.app.pc.record_sessions()
        f.app.clocking.clock_in(None, None)
        f.power.boot_list = [Boot("morning", at("2026-10-14T08:30:00"), at("2026-10-14T12:10:00"), False),
                             Boot("after", at("2026-10-14T12:13:00"), at("2026-10-14T12:13:00"), True)]
        f.power.booted = "after"
        f.at("2026-10-14T12:13:30")
        Reminders(f.app.log, f.app.clocking, f.app.pc, f.desktop, "http://page/").on_login()
        f.desktop.click("Your PC was off 12:10–12:13")
        self.assertEqual(f.desktop.opened, ["http://page/#explain-break"])


class LunchPerLabel(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:30:00")
        self.f.app.setup.configure("12:00 for 60 min", "08:30 to 17:30", "Northwind")
        self.f.app.labels.create("Globex", "08:00 to 14:00", "")
        self.f.app.labels.create("Late lunch", "09:00 to 18:00", "13:30 for 30 min")

    def lunch_prompts(self, label: str, moment: str) -> list[str]:
        self.f.app.clocking.clock_in(None, None, label, off_default=True)
        self.f.at(moment)
        Reminders(self.f.app.log, self.f.app.clocking, self.f.app.pc, self.f.desktop, "http://page/").tick()
        return [summary for summary, _ in self.f.desktop.notices if summary == "Lunch time"]

    def test_a_label_without_lunch_is_never_asked(self):
        self.assertEqual(self.lunch_prompts("Globex", "2026-10-14T12:00:30"), [])

    def test_a_label_is_asked_at_its_own_lunch_time(self):
        self.assertEqual(self.lunch_prompts("Late lunch", "2026-10-14T13:30:30"), ["Lunch time"])


if __name__ == "__main__":
    unittest.main()
