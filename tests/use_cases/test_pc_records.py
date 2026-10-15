import unittest
from datetime import timedelta

from chronata.timekeeping.pc_sessions import Boot
from tests.fakes import Fixture, at


class PowerSessions(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T09:00:00")
        self.f.power.boot_list = [Boot("yesterday", at("2026-10-13T08:30:00"), at("2026-10-13T19:12:52"), False),
                                  Boot("today", at("2026-10-14T08:29:56"), at("2026-10-14T09:00:00"), True)]

    def test_each_session_is_recorded_once(self):
        self.f.app.pc.record_sessions()
        self.assertIsNone(self.f.app.pc.record_sessions())
        self.assertEqual([(s.boot, s.off) for s in self.f.app.log.pc_sessions()], [("yesterday", at("2026-10-13T19:12:52")), ("today", None)])

    def test_an_exact_shutdown_time_is_kept_over_the_journal_guess(self):
        self.f.app.pc.record_sessions()
        self.f.at("2026-10-14T18:02:09")
        self.f.app.pc.record_shutdown()
        self.f.power.boot_list = [Boot("today", at("2026-10-14T08:29:56"), at("2026-10-14T18:02:15"), False),
                                  Boot("tomorrow", at("2026-10-15T08:00:00"), at("2026-10-15T08:00:00"), True)]
        self.f.power.booted = "tomorrow"
        self.f.app.pc.record_sessions()
        today = next(s for s in self.f.app.log.pc_sessions() if s.boot == "today")
        self.assertEqual((today.off, today.exact), (at("2026-10-14T18:02:09"), True))


class PcOffDuringAShift(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:31:00")
        self.f.power.boot_list = [Boot("morning", at("2026-10-14T08:30:00"), at("2026-10-14T08:31:00"), True)]
        self.f.power.booted = "morning"
        self.f.app.pc.record_sessions()
        self.f.app.clocking.clock_in(None, None)

    def restart(self, went_off: str, came_on: str) -> None:
        self.f.power.boot_list = [Boot("morning", at("2026-10-14T08:30:00"), at(went_off), False),
                                  Boot("after", at(came_on), at(came_on), True)]
        self.f.power.booted = "after"
        self.f.at(came_on)
        self.f.app.pc.record_sessions()

    def test_the_same_day_the_off_time_is_a_break_and_the_shift_carries_on(self):
        self.restart("2026-10-14T12:10:00", "2026-10-14T12:13:00")
        self.assertIsNone(self.f.app.pc.interrupted())
        self.f.at("2026-10-14T17:31:00")
        self.f.app.clocking.clock_out(None, None)
        self.assertEqual(self.f.app.log.weeks()[0].days[0].worked, timedelta(hours=8, minutes=57))

    def test_a_reason_can_be_added_for_the_off_time(self):
        self.restart("2026-10-14T12:10:00", "2026-10-14T12:13:00")
        shift = self.f.app.log.shifts()[0]
        self.f.app.corrections.explain_break(shift.id, shift.breaks[0].start.isoformat(), "power cut")
        self.assertEqual(self.f.app.log.shifts()[0].breaks[0].reason, "power cut")

    def test_off_overnight_offers_to_clock_out_at_the_shutdown(self):
        self.restart("2026-10-14T19:12:52", "2026-10-15T08:00:00")
        self.assertEqual(self.f.app.pc.interrupted().pc_went_off, at("2026-10-14T19:12:52"))


if __name__ == "__main__":
    unittest.main()
