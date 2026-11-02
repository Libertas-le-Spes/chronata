import unittest
from datetime import time, timedelta

from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.measuring_moment import MeasuringMoment
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.shifts.shifts import Shift
from tests.fakes import at

HOURS = WorkingDay(time(8), time(17))
MORNING = ClockedDay(at("2026-10-15T08:00:00").date(), (Shift(1, at("2026-10-15T08:00:00"), at("2026-10-15T11:00:00"), timedelta()),))


class HowFarADayIsMeasured(unittest.TestCase):
    def test_a_past_day_is_measured_in_full(self):
        self.assertIsNone(MeasuringMoment(at("2026-10-16T10:00:00"), False).judged_at(MORNING, HOURS))

    def test_while_clocked_in_today_is_measured_up_to_now(self):
        self.assertEqual(MeasuringMoment(at("2026-10-15T12:30:00"), True).judged_at(MORNING, HOURS), time(12, 30))

    def test_clocked_out_before_the_shift_ends_today_is_measured_up_to_the_last_clock_out(self):
        self.assertEqual(MeasuringMoment(at("2026-10-15T12:30:00"), False).judged_at(MORNING, HOURS), time(11))

    def test_at_the_moment_the_shift_ends_today_is_measured_in_full(self):
        self.assertIsNone(MeasuringMoment(at("2026-10-15T17:00:00"), False).judged_at(MORNING, HOURS))

    def test_once_the_shift_is_over_today_is_measured_in_full(self):
        self.assertIsNone(MeasuringMoment(at("2026-10-15T17:30:00"), False).judged_at(MORNING, HOURS))


if __name__ == "__main__":
    unittest.main()
