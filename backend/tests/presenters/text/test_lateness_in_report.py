import unittest
from datetime import date, time, timedelta

from chronata.presenters.text.text_report import report_lines
from chronata.timekeeping.compensation.compensation import reconcile_by_label
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.timesheet import weeks
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.shifts.shifts import Shift
from tests.fakes import at

HOURS = LabelHours("Primary")
WEEKS = {"Primary": weeks([Shift(1, at("2026-10-05T08:00:00"), at("2026-10-05T18:00:00"), timedelta()),
                             Shift(2, at("2026-10-06T08:12:00"), at("2026-10-06T16:05:00"), timedelta())], WorkingDay(time(8), time(16)))}


class LatenessInTheReport(unittest.TestCase):
    def setUp(self):
        self.lines = report_lines(WEEKS, reconcile_by_label([], WEEKS, HOURS), date(2026, 10, 20))

    def test_each_day_with_lateness_not_covered_is_listed_under_its_label(self):
        self.assertIn("    2026-10-06 Tue: -0:07", self.lines)

    def test_the_totals_take_compensation_and_lateness_off_the_overtime_worked(self):
        totals = self.lines[self.lines.index("All labels"):]
        self.assertEqual(totals, ["All labels",
                                  "  Overtime worked:                2:00",
                                  "  Compensated:                   -0:00",
                                  "  Lateness not covered:          -0:07",
                                  "  Unpaid:                         1:53"])


if __name__ == "__main__":
    unittest.main()
