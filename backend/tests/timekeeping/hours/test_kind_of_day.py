import unittest
from datetime import date, time

from chronata.timekeeping.hours.day_kinds.day_off import DayOff
from chronata.timekeeping.hours.day_kinds.kind_of_day import kind_of_day
from chronata.timekeeping.hours.day_kinds.workday import Workday
from chronata.timekeeping.hours.working_day import WorkingDay

MONDAY_TO_THURSDAY = WorkingDay(time(8), time(17), workdays=frozenset(range(4)))


class KindOfDay(unittest.TestCase):
    def test_a_day_in_the_working_week_is_a_workday(self):
        self.assertIsInstance(kind_of_day(MONDAY_TO_THURSDAY, date(2026, 10, 15)), Workday)

    def test_a_day_outside_the_working_week_is_a_day_off(self):
        self.assertIsInstance(kind_of_day(MONDAY_TO_THURSDAY, date(2026, 10, 16)), DayOff)


if __name__ == "__main__":
    unittest.main()
