import unittest
from datetime import time, timedelta

from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.day_kinds.day_off import DayOff
from chronata.timekeeping.hours.day_kinds.hours_not_set import HoursNotSet
from chronata.timekeeping.hours.day_kinds.kind_of_day import kind_of_day
from chronata.timekeeping.hours.day_kinds.workday import Workday
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.shifts.shifts import Shift
from chronata.timekeeping.shifts.start_answer import StartAnswer
from tests.fakes import at

MONDAY_TO_THURSDAY = WorkingDay(time(8), time(17), workdays=frozenset(range(4)))


def clocked_on(day: str, answer: StartAnswer = StartAnswer()) -> ClockedDay:
    shift = Shift(1, at(f"{day}T18:00:00"), at(f"{day}T20:00:00"), timedelta())
    shift.start_answer = answer
    return ClockedDay(shift.start.date(), (shift,), True)


class KindOfDay(unittest.TestCase):
    def test_a_day_in_the_working_week_is_a_workday(self):
        self.assertIsInstance(kind_of_day(MONDAY_TO_THURSDAY, clocked_on("2026-10-15")), Workday)

    def test_a_day_outside_the_working_week_is_a_day_off(self):
        self.assertIsInstance(kind_of_day(MONDAY_TO_THURSDAY, clocked_on("2026-10-16")), DayOff)

    def test_a_day_for_a_label_without_hours_is_only_counted(self):
        self.assertIsInstance(kind_of_day(None, clocked_on("2026-10-15")), HoursNotSet)

    def test_a_workday_started_after_the_shift_and_called_overtime_counts_like_a_day_off(self):
        self.assertIsInstance(kind_of_day(MONDAY_TO_THURSDAY, clocked_on("2026-10-15", StartAnswer(overtime=True))), DayOff)

    def test_a_workday_started_after_the_shift_as_normal_hours_stays_a_workday(self):
        self.assertIsInstance(kind_of_day(MONDAY_TO_THURSDAY, clocked_on("2026-10-15", StartAnswer(normal_hours=True))), Workday)


if __name__ == "__main__":
    unittest.main()
