import unittest

from chronata.presenters.page.day_lines import DayRecords, day_lines
from chronata.timekeeping.pc.pc_sessions import Boot
from chronata.timekeeping.shifts.day_entries import day_entries
from tests.fakes import Fixture, at


class OneBlockForTheDay(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-15T08:41:52")
        self.f.app.setup.configure("12:00 for 60 min", "08:30 to 17:30", "Northwind")
        self.f.power.boot_list = [Boot("today", at("2026-10-15T08:41:52"), at("2026-10-15T08:41:52"), True)]
        self.f.app.pc.record_sessions()
        self.step("2026-10-15T09:04:59", lambda app: app.clocking.clock_in(None, None))
        self.step("2026-10-15T09:40:00", lambda app: app.corrections.add("2026-10-15", "08:41:52", "09:04:59", "worked from when the PC came on", None, "Northwind"))
        self.step("2026-10-15T12:01:32", lambda app: app.clocking.clock_out(None, "Stepping out."))
        self.step("2026-10-15T13:06:05", lambda app: app.clocking.clock_in(None, None))

    def step(self, when: str, action) -> None:
        self.f.at(when)
        action(self.f.app)

    def lines(self, day: str = "2026-10-15") -> list[tuple]:
        entry = next(e for e in day_entries(self.f.app.log.shifts()) if e.day.isoformat() == day)
        records = DayRecords(self.f.app.log.pc_sessions(), [], self.f.now)
        return [(line["what"], (line["at"] or "")[11:19], line["detail"], line["mistake"]) for line in day_lines(entry, records)]

    def test_the_pc_leads_and_the_manual_clock_ins_follow(self):
        self.assertEqual(self.lines(), [
            ("PC on", "08:41:52", "not yet independently timestamped", None),
            ("Manual clock in", "09:04:59", "", None),
            ("Manual clock out", "12:01:32", "“Stepping out.”", None),
            ("Manual clock in", "13:06:05", "12:01–13:06 not counted", None),
        ])

    def test_a_correction_goes_on_top_and_the_pc_and_manual_times_stay(self):
        self.step("2026-10-15T18:00:00", lambda app: app.clocking.clock_out(None, None))
        ids = [shift.id for shift in self.f.app.log.shifts()]
        self.step("2026-10-15T18:05:00", lambda app: app.corrections.correct(ids, "08:30", None, "early meeting"))
        self.assertEqual(self.lines()[:3], [
            ("Corrected", "", "08:30:00 – 18:00:00 · changed Thu 15 Oct 18:05 · “early meeting”", None),
            ("PC on", "08:41:52", "not yet independently timestamped", None),
            ("Manual clock in", "09:04:59", "", None),
        ])

    def test_time_added_later_in_a_clocked_day_can_be_marked_a_mistake_on_its_own(self):
        self.step("2026-10-15T18:00:00", lambda app: app.clocking.clock_out(None, None))
        self.step("2026-10-16T08:00:00", lambda app: app.corrections.add("2026-10-15", "20:00", "21:00", "forgot", None, "Northwind"))
        added = self.lines()[-1]
        self.assertEqual(added[:3], ("Added later", "20:00:00", "20:00:00 – 21:00:00 · written down Fri 16 Oct 08:00 · “forgot”"))
        self.assertIsNotNone(added[3])

    def test_a_day_typed_in_whole_has_only_the_day_buttons(self):
        self.step("2026-10-16T08:00:00", lambda app: app.corrections.add("2026-10-14", "09:00", "17:00", "forgot to clock", None, "Northwind"))
        self.assertEqual([line[3] for line in self.lines("2026-10-14")], [None])
