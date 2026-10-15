import unittest

from chronata.presenters.text.text_report import entry_lines
from chronata.timekeeping.pc.pc_sessions import Boot
from chronata.timekeeping.shifts.day_entries import day_entries
from tests.fakes import Fixture, at, hours


class TheShiftsList(unittest.TestCase):
    def test_a_day_is_one_block_led_by_the_pc_with_its_shift_numbers_in_the_header(self):
        f = Fixture("2026-10-15T08:41:52")
        f.app.setup.configure(hours("08:30", "17:30", "12:00", "60"), "Northwind")
        f.power.boot_list = [Boot("today", at("2026-10-15T08:41:52"), at("2026-10-15T08:41:52"), True)]
        f.app.pc.record_sessions()
        f.at("2026-10-15T09:04:59")
        f.app.clocking.clock_in(None, None)
        f.at("2026-10-15T09:40:00")
        f.app.corrections.add("2026-10-15", "08:41:52", "09:04:59", "worked from when the PC came on", None, "Northwind")
        lines = entry_lines(day_entries(f.app.log.shifts()), f.app.log.pc_sessions(), [], f.now)
        self.assertEqual(lines[1:], [
            "2026-10-15  08:41:52  --:--:--    0:58  Northwind, OPEN, PC on 100%, shifts 2, 3",
            "      PC on               08:41:52          not yet independently timestamped",
            "      Manual clock in     09:04:59",
        ])
