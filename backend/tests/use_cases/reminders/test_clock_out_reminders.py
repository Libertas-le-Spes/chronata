import unittest

from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions.questions import Answers
from chronata.use_cases.reminders.reminders import Reminders
from tests.fakes import Fixture, hours

CLOCK_OUT_REMINDERS = ("Your shift ended", "Still working on your day off?")


class ClockOutReminders(unittest.TestCase):
    def start(self, moment: str, answers: Answers = Answers()) -> None:
        self.f = Fixture(moment)
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")
        self.f.app.clocking.clock_in(None, None, None, answers)
        self.reminders = Reminders(self.f.app.log, self.f.app.clocking, self.f.app.pc, self.f.desktop, self.f.page, self.f.app.reminder_setting)

    def reminded_at(self, day: str, *moments: str) -> list[str]:
        reminded = []
        for moment in moments:
            self.f.at(f"{day}T{moment}:00")
            before = len(self.f.desktop.notices)
            self.reminders.tick()
            for summary, _ in self.f.desktop.notices[before:]:
                if summary.startswith(CLOCK_OUT_REMINDERS):
                    reminded.append(moment)
        return reminded


class OnAWorkday(ClockOutReminders):
    def test_it_comes_when_the_shift_ends_and_every_half_hour_after(self):
        self.start("2026-10-14T08:00:00")
        self.assertEqual(self.reminded_at("2026-10-14", "16:59", "17:00", "17:10", "17:29", "17:30", "18:00"), ["17:00", "17:30", "18:00"])

    def test_it_says_when_the_shift_ended(self):
        self.start("2026-10-14T08:00:00")
        self.reminded_at("2026-10-14", "17:00")
        self.assertEqual(self.f.desktop.notices[-1][0], "Your shift ended at 17:00")

    def test_a_chosen_pace_is_kept_to(self):
        self.start("2026-10-14T08:00:00")
        self.f.app.reminder_setting.remind_every(15)
        self.assertEqual(self.reminded_at("2026-10-14", "17:00", "17:14", "17:15", "17:30"), ["17:00", "17:15", "17:30"])

    def test_turned_off_it_never_comes(self):
        self.start("2026-10-14T08:00:00")
        self.f.app.reminder_setting.turn_off()
        self.assertEqual(self.reminded_at("2026-10-14", "17:00", "18:00"), [])

    def test_clocking_in_after_the_shift_waits_one_pace_before_the_first(self):
        self.start("2026-10-14T19:00:00", Answers(overtime=True))
        self.assertEqual(self.reminded_at("2026-10-14", "19:00", "19:29", "19:30"), ["19:30"])

    def test_a_shift_left_running_overnight_keeps_reminding(self):
        self.start("2026-10-14T08:00:00")
        self.reminded_at("2026-10-14", "23:50")
        self.assertEqual(self.reminded_at("2026-10-15", "00:20", "00:30"), ["00:20"])

    def test_after_midnight_the_shift_end_is_still_the_day_it_started(self):
        self.start("2026-10-14T08:00:00")
        self.assertEqual(self.reminded_at("2026-10-15", "00:20"), ["00:20"])

    def test_coming_back_after_clocking_out_starts_the_pace_again(self):
        self.start("2026-10-14T08:00:00")
        self.reminded_at("2026-10-14", "17:00")
        self.f.at("2026-10-14T17:05:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T17:20:00")
        self.f.app.clocking.clock_in(None, None, None, Answers(normal_hours=True))
        self.assertEqual(self.reminded_at("2026-10-14", "17:30", "17:49", "17:50"), ["17:50"])

    def test_a_pace_changed_after_one_reminder_sets_the_next(self):
        self.start("2026-10-14T08:00:00")
        self.reminded_at("2026-10-14", "17:00")
        self.f.app.reminder_setting.remind_every(240)
        self.assertEqual(self.reminded_at("2026-10-14", "17:30", "20:59", "21:00"), ["21:00"])

    def test_after_the_service_restarts_the_first_tick_past_the_shift_end_reminds(self):
        self.start("2026-10-14T08:00:00")
        self.reminded_at("2026-10-14", "17:00")
        self.reminders = Reminders(self.f.app.log, self.f.app.clocking, self.f.app.pc, self.f.desktop, self.f.page, self.f.app.reminder_setting)
        self.assertEqual(self.reminded_at("2026-10-14", "17:05", "17:20", "17:35"), ["17:05", "17:35"])

    def test_it_replaces_the_twelve_hour_reminder(self):
        self.start("2026-10-14T08:00:00")
        self.reminded_at("2026-10-14", "19:30")
        self.f.at("2026-10-14T20:00:00")
        before = len(self.f.desktop.notices)
        self.reminders.tick()
        self.assertEqual([summary for summary, _ in self.f.desktop.notices[before:]], ["Your shift ended at 17:00"])

    def test_clicking_it_clocks_out(self):
        self.start("2026-10-14T08:00:00")
        self.reminded_at("2026-10-14", "17:00")
        self.f.desktop.click("Your shift ended")
        self.assertIsNotNone(self.f.app.log.shifts()[0].end)


class OnADayOff(ClockOutReminders):
    def test_it_comes_every_hour_from_clocking_in(self):
        self.start("2026-10-17T09:00:00")
        self.assertEqual(self.reminded_at("2026-10-17", "09:30", "09:59", "10:00", "10:30", "11:00"), ["10:00", "11:00"])

    def test_the_chosen_pace_does_not_change_it(self):
        self.start("2026-10-17T09:00:00")
        self.f.app.reminder_setting.remind_every(15)
        self.assertEqual(self.reminded_at("2026-10-17", "09:15", "10:00", "10:15"), ["10:00"])

    def test_turned_off_it_never_comes(self):
        self.start("2026-10-17T09:00:00")
        self.f.app.reminder_setting.turn_off()
        self.assertEqual(self.reminded_at("2026-10-17", "10:00", "11:00"), [])


class OnALabelWithoutSetHours(ClockOutReminders):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")
        self.f.app.labels.create("Secondary", Answers(no_set_hours=True))
        self.f.app.clocking.clock_in(None, None, "Secondary", Answers(off_default=True))
        self.reminders = Reminders(self.f.app.log, self.f.app.clocking, self.f.app.pc, self.f.desktop, self.f.page, self.f.app.reminder_setting)

    def test_it_never_comes_because_there_is_no_shift_end(self):
        self.assertEqual(self.reminded_at("2026-10-14", "17:00", "18:00"), [])

    def test_the_twelve_hour_reminder_still_comes(self):
        self.reminded_at("2026-10-14", "20:00")
        self.assertEqual(self.f.desktop.notices[-1][0], "Still working?")


class OnAnUnlabelledShift(ClockOutReminders):
    def test_the_default_labels_shift_end_is_used(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")
        self.f.app.clocking.clock_in(None, None, "", Answers(off_default=True))
        self.reminders = Reminders(self.f.app.log, self.f.app.clocking, self.f.app.pc, self.f.desktop, self.f.page, self.f.app.reminder_setting)
        self.assertEqual(self.reminded_at("2026-10-14", "16:59", "17:00"), ["17:00"])


class ChoosingThePace(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")

    def test_it_starts_at_every_half_hour(self):
        self.assertEqual(self.f.app.reminder_setting.current().every.total_seconds(), 1800)

    def test_a_choice_is_remembered(self):
        self.f.app.reminder_setting.remind_every(45)
        self.assertEqual(self.f.app.reminder_setting.current().every.total_seconds(), 2700)

    def test_turning_them_off_is_remembered(self):
        self.f.app.reminder_setting.turn_off()
        self.assertTrue(self.f.app.reminder_setting.current().off)

    def test_paces_outside_five_to_two_hundred_and_forty_minutes_are_refused(self):
        for minutes in (4, 241, 0, -30):
            with self.subTest(minutes=minutes), self.assertRaises(UserError):
                self.f.app.reminder_setting.remind_every(minutes)

    def test_the_edges_are_allowed(self):
        for minutes in (5, 240):
            with self.subTest(minutes=minutes):
                self.f.app.reminder_setting.remind_every(minutes)
                self.assertEqual(self.f.app.reminder_setting.current().every.total_seconds(), minutes * 60)

    def test_a_pace_that_is_not_a_whole_number_is_refused(self):
        for given in ("30", 30.5, True, None):
            with self.subTest(given=given), self.assertRaises(UserError):
                self.f.app.reminder_setting.remind_every(given)


if __name__ == "__main__":
    unittest.main()
