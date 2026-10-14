import unittest
from datetime import date, datetime, time, timedelta

from chronata.timekeeping.pay import reconcile
from chronata.timekeeping.record import Entry
from chronata.timekeeping.shifts import Shift
from chronata.timekeeping.working_day import WorkingDay, weeks
from tests.fakes import SAST, at

NO_LUNCH = WorkingDay(time(8), time(16), time(12), 0, frozenset(range(5)), 40, True)


def overtime_on(*days: tuple[str, str, str]):
    return weeks([Shift(1, at(f"{d}T{s}"), at(f"{d}T{e}"), timedelta()) for d, s, e in days], NO_LUNCH)


def payslip(start: str, end: str, paid_hours: float, kind: str = "paid") -> Entry:
    return Entry(1, "compensation", datetime.now(SAST), {"from": start, "to": end, "hours": paid_hours, "kind": kind})


class Reconciling(unittest.TestCase):
    def test_a_pay_period_ending_mid_week_takes_only_its_own_days(self):
        result = reconcile([payslip("2026-09-26", "2026-10-09", 0)], overtime_on(("2026-10-09", "08:00", "10:00"), ("2026-10-10", "09:00", "12:00")))
        self.assertEqual(result.periods[0].shortfall, timedelta())
        self.assertEqual([d.date for d in result.unmatched], [date(2026, 10, 10)])

    def test_unpaid_overtime_shows_as_a_shortfall(self):
        result = reconcile([payslip("2026-10-01", "2026-10-31", 1), payslip("2026-10-01", "2026-10-31", 0.5, "time_off")],
                           overtime_on(("2026-10-05", "08:00", "19:00")))
        self.assertEqual(result.shortfall, timedelta(hours=1, minutes=30))


if __name__ == "__main__":
    unittest.main()
