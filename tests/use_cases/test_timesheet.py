import unittest
from datetime import timedelta

from chronata.timekeeping.pc_sessions import Boot
from chronata.use_cases.outcome import OffDefaultLabel, UnconfirmedLabel, UserError
from tests.fakes import Fixture, at


class SameDayShifts(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:03:00")
        self.f.sheet.configure("12:00 for 60 min", "08:00 to 17:00")
        self.f.sheet.clock_in(None, None, "Acme")

    def test_clocking_back_in_the_same_day_continues_the_shift_without_counting_the_break(self):
        self.f.at("2026-10-14T10:00:00")
        self.f.sheet.clock_out(None, None)
        self.f.at("2026-10-14T10:04:00")
        self.f.sheet.clock_in(None, None)
        self.f.at("2026-10-14T17:03:00")
        self.f.sheet.clock_out(None, None)
        self.assertEqual(len(self.f.sheet.shifts()), 1)
        self.assertEqual(self.f.sheet.weeks()[0].days[0].worked, timedelta(hours=8, minutes=56))

    def test_clocking_back_in_on_another_label_starts_a_new_shift(self):
        self.f.at("2026-10-14T10:00:00")
        self.f.sheet.clock_out(None, None)
        self.f.at("2026-10-14T10:04:00")
        self.f.sheet.clock_in(None, None, "Globex")
        self.assertEqual([(s.label, s.end) for s in self.f.sheet.shifts()], [("Acme", at("2026-10-14T10:00:00")), ("Globex", None)])

    def test_clocking_back_in_on_the_same_label_continues_the_shift(self):
        self.f.at("2026-10-14T10:00:00")
        self.f.sheet.clock_out(None, None)
        self.f.at("2026-10-14T10:04:00")
        self.f.sheet.clock_in(None, None, "acme")
        self.assertEqual(len(self.f.sheet.shifts()), 1)

    def test_a_label_change_stays_on_the_record(self):
        self.f.at("2026-10-14T12:00:00")
        self.f.sheet.clock_out(None, None)
        self.f.sheet.label(self.f.sheet.shifts()[0].id, "Globex")
        shift = self.f.sheet.shifts()[0]
        self.assertEqual(shift.label, "Globex")
        self.assertIn("label changed from Acme to Globex", shift.changes[-1])

    def test_setting_up_the_working_day(self):
        self.f.sheet.configure("12h30 for 30 min", "07:30 to 16:00")
        self.assertEqual(self.f.sheet.working_day.daily_hours, 8.0)
        with self.assertRaises(UserError):
            self.f.sheet.configure("12:00", "")


class Labels(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T17:00:00")
        self.f.sheet.add("2026-10-13", "08:00", "12:00", "written later", None, "Northwind")

    def labels_of_shifts(self) -> list[str]:
        return [shift.label for shift in self.f.sheet.shifts()]

    def test_the_existing_spelling_is_used_whatever_the_capitals(self):
        self.f.sheet.add("2026-10-14", "08:00", "12:00", "written later", None, "northwind ")
        self.assertEqual(self.labels_of_shifts(), ["Northwind", "Northwind"])

    def test_a_near_miss_needs_confirming_before_it_becomes_a_new_label(self):
        with self.assertRaises(UnconfirmedLabel) as raised:
            self.f.sheet.add("2026-10-14", "08:00", "12:00", "written later", None, "Northwnid")
        self.assertEqual(raised.exception.near_misses, ("Northwind",))
        self.f.sheet.add("2026-10-14", "08:00", "12:00", "written later", None, "Northwnid", new_label=True)
        self.assertIn("Northwnid", self.labels_of_shifts())

    def test_renaming_moves_every_shift_and_stays_on_the_record(self):
        self.f.sheet.add("2026-10-14", "08:00", "12:00", "written later", None, "Northwind")
        outcome = self.f.sheet.rename_label("northwind", "Northwind Ltd")
        self.assertEqual(self.labels_of_shifts(), ["Northwind Ltd", "Northwind Ltd"])
        self.assertIn("on 2 shifts", outcome.message)
        self.assertIn("label changed from Northwind to Northwind Ltd", self.f.sheet.shifts()[0].changes[-1])

    def test_renaming_onto_an_existing_label_merges_them(self):
        self.f.sheet.add("2026-10-14", "08:00", "12:00", "written later", None, "Acme")
        outcome = self.f.sheet.rename_label("Acme", "northwind")
        self.assertEqual(self.labels_of_shifts(), ["Northwind", "Northwind"])
        self.assertTrue(outcome.message.startswith("merged Acme into Northwind"))

    def test_the_readable_folder_follows_a_rename(self):
        self.f.sheet.rename_label("Northwind", "Northwind Ltd")
        self.assertTrue((self.f.data / "Northwind Ltd" / "Days" / "2026-10-13.md").exists())
        self.assertFalse((self.f.data / "Northwind").exists())


class DefaultLabel(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.sheet.configure("12:00 for 60 min", "08:00 to 17:00", "Northwind")

    def test_on_a_workday_another_label_asks_first_and_records_nothing(self):
        with self.assertRaises(OffDefaultLabel) as raised:
            self.f.sheet.clock_in(None, None, "Acme")
        self.assertEqual((raised.exception.label, raised.exception.default_label), ("Acme", "Northwind"))
        self.assertEqual(self.f.sheet.shifts(), [])

    def test_confirming_clocks_in_on_the_other_label(self):
        self.f.sheet.clock_in(None, None, "Acme", off_default=True)
        self.assertEqual(self.f.sheet.shifts()[0].label, "Acme")

    def test_no_label_on_a_workday_asks_too(self):
        with self.assertRaises(OffDefaultLabel):
            self.f.sheet.clock_in(None, None, "")

    def test_the_default_goes_straight_in_whatever_the_capitals(self):
        self.f.sheet.clock_in(None, None, " northwind")
        self.assertEqual(self.f.sheet.shifts()[0].label, "Northwind")

    def test_clocking_in_without_choosing_uses_the_default(self):
        self.f.sheet.clock_in(None, None)
        self.assertEqual(self.f.sheet.shifts()[0].label, "Northwind")

    def test_at_the_weekend_another_label_does_not_ask(self):
        self.f.at("2026-10-17T10:00:00")
        self.f.sheet.clock_in(None, None, "Acme")
        self.assertEqual(self.f.sheet.shifts()[0].label, "Acme")

    def test_without_a_default_nothing_asks(self):
        self.f.sheet.set_default_label("")
        self.f.sheet.clock_in(None, None, "Acme")
        self.assertEqual(self.f.sheet.shifts()[0].label, "Acme")

    def test_the_default_takes_the_existing_spelling(self):
        self.f.sheet.clock_in(None, None, "Acme", off_default=True)
        self.f.sheet.set_default_label("ACME")
        self.assertEqual(self.f.sheet.working_day.default_label, "Acme")

    def test_renaming_the_default_label_keeps_it_the_default(self):
        self.f.sheet.clock_in(None, None)
        self.f.sheet.rename_label("Northwind", "Northwind Ltd")
        self.assertEqual(self.f.sheet.working_day.default_label, "Northwind Ltd")

    def test_leaving_the_setup_answer_out_keeps_the_default(self):
        self.f.sheet.configure("12:00 for 30 min", "08:00 to 16:30")
        self.assertEqual(self.f.sheet.working_day.default_label, "Northwind")


class PowerSessions(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T09:00:00")
        self.f.power.boot_list = [Boot("yesterday", at("2026-10-13T08:30:00"), at("2026-10-13T19:12:52"), False),
                                  Boot("today", at("2026-10-14T08:29:56"), at("2026-10-14T09:00:00"), True)]

    def test_each_session_is_recorded_once(self):
        self.f.sheet.record_pc_sessions()
        self.assertIsNone(self.f.sheet.record_pc_sessions())
        self.assertEqual([(s.boot, s.off) for s in self.f.sheet.pc_sessions()], [("yesterday", at("2026-10-13T19:12:52")), ("today", None)])

    def test_an_exact_shutdown_time_is_kept_over_the_journal_guess(self):
        self.f.sheet.record_pc_sessions()
        self.f.at("2026-10-14T18:02:09")
        self.f.sheet.record_shutdown()
        self.f.power.boot_list = [Boot("today", at("2026-10-14T08:29:56"), at("2026-10-14T18:02:15"), False),
                                  Boot("tomorrow", at("2026-10-15T08:00:00"), at("2026-10-15T08:00:00"), True)]
        self.f.power.booted = "tomorrow"
        self.f.sheet.record_pc_sessions()
        today = next(s for s in self.f.sheet.pc_sessions() if s.boot == "today")
        self.assertEqual((today.off, today.exact), (at("2026-10-14T18:02:09"), True))


class PcOffDuringAShift(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:31:00")
        self.f.power.boot_list = [Boot("morning", at("2026-10-14T08:30:00"), at("2026-10-14T08:31:00"), True)]
        self.f.power.booted = "morning"
        self.f.sheet.record_pc_sessions()
        self.f.sheet.clock_in(None, None)

    def restart(self, went_off: str, came_on: str) -> None:
        self.f.power.boot_list = [Boot("morning", at("2026-10-14T08:30:00"), at(went_off), False),
                                  Boot("after", at(came_on), at(came_on), True)]
        self.f.power.booted = "after"
        self.f.at(came_on)
        self.f.sheet.record_pc_sessions()

    def test_the_same_day_the_off_time_is_a_break_and_the_shift_carries_on(self):
        self.restart("2026-10-14T12:10:00", "2026-10-14T12:13:00")
        self.assertIsNone(self.f.sheet.interrupted())
        self.f.at("2026-10-14T17:31:00")
        self.f.sheet.clock_out(None, None)
        self.assertEqual(self.f.sheet.weeks()[0].days[0].worked, timedelta(hours=8, minutes=57))

    def test_a_reason_can_be_added_for_the_off_time(self):
        self.restart("2026-10-14T12:10:00", "2026-10-14T12:13:00")
        shift = self.f.sheet.shifts()[0]
        self.f.sheet.explain_break(shift.id, shift.breaks[0].start.isoformat(), "power cut")
        self.assertEqual(self.f.sheet.shifts()[0].breaks[0].reason, "power cut")

    def test_off_overnight_offers_to_clock_out_at_the_shutdown(self):
        self.restart("2026-10-14T19:12:52", "2026-10-15T08:00:00")
        self.assertEqual(self.f.sheet.interrupted().pc_went_off, at("2026-10-14T19:12:52"))


if __name__ == "__main__":
    unittest.main()
