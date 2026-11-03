import unittest
from datetime import time, timedelta

from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.day_kinds.day_off import DayOff
from chronata.timekeeping.hours.day_kinds.hours_not_set import HoursNotSet
from chronata.timekeeping.hours.day_kinds.kind_of_day import kind_of_day
from chronata.timekeeping.hours.day_kinds.normal_hours_after_shift import NormalHoursAfterShift
from chronata.timekeeping.hours.day_kinds.overtime_after_shift import OvertimeAfterShift
from chronata.timekeeping.hours.day_kinds.workday import Workday
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.shifts.shifts import Shift
from chronata.timekeeping.shifts.start_answer import StartAnswer
from tests.fakes import at

MONDAY_TO_THURSDAY = WorkingDay(time(8), time(17), workdays=frozenset(range(4)))


def clocked_on(day: str, answer: StartAnswer = StartAnswer(), start: str = "18:00") -> ClockedDay:
    shift = Shift(1, at(f"{day}T{start}:00"), at(f"{day}T20:00:00"), timedelta())
    shift.start_answer = answer
    return ClockedDay(shift.start.date(), "", (shift,), True)


class KindOfDay(unittest.TestCase):
    def test_a_day_in_the_working_week_is_a_workday(self):
        self.assertIs(type(kind_of_day(MONDAY_TO_THURSDAY, clocked_on("2026-10-15", StartAnswer(), "09:00"))), Workday)

    def test_a_day_outside_the_working_week_is_a_day_off(self):
        self.assertIsInstance(kind_of_day(MONDAY_TO_THURSDAY, clocked_on("2026-10-16")), DayOff)

    def test_a_day_for_a_label_without_hours_is_only_counted(self):
        self.assertIsInstance(kind_of_day(None, clocked_on("2026-10-15")), HoursNotSet)

    def test_a_workday_started_after_the_shift_and_called_overtime_is_overtime_after_the_shift(self):
        self.assertIsInstance(kind_of_day(MONDAY_TO_THURSDAY, clocked_on("2026-10-15", StartAnswer(overtime_after_shift=True, label=""))), OvertimeAfterShift)

    def test_an_overtime_answer_on_a_shift_corrected_to_start_during_the_shift_no_longer_counts(self):
        corrected = clocked_on("2026-10-15", StartAnswer(overtime_after_shift=True, label=""), "08:30")
        self.assertIs(type(kind_of_day(MONDAY_TO_THURSDAY, corrected)), Workday)

    def test_a_workday_started_after_the_shift_as_normal_hours_is_normal_hours_after_the_shift(self):
        self.assertIsInstance(kind_of_day(MONDAY_TO_THURSDAY, clocked_on("2026-10-15", StartAnswer(overtime_after_shift=False, label=""))), NormalHoursAfterShift)


if __name__ == "__main__":
    unittest.main()
