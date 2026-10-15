import unittest
from datetime import date, datetime, time, timedelta

from chronata.timekeeping.compensation import all_labels, reconcile, reconcile_by_label
from chronata.timekeeping.record import Entry
from chronata.timekeeping.shifts import Shift
from chronata.timekeeping.overtime import weeks
from chronata.timekeeping.working_day import WorkingDay
from tests.fakes import SAST, at

NO_LUNCH = WorkingDay(time(8), time(16))


def overtime_on(*days: tuple[str, str, str]):
    return weeks([Shift(1, at(f"{d}T{s}"), at(f"{d}T{e}"), timedelta()) for d, s, e in days], NO_LUNCH)


def compensated(start: str, end: str, hours: float, kind: str = "paid", label: str | None = None) -> Entry:
    data = {"from": start, "to": end, "hours": hours, "kind": kind, **({"label": label} if label else {})}
    return Entry(1, "compensation", datetime.now(SAST), data)


class Reconciling(unittest.TestCase):
    def test_a_period_ending_mid_week_takes_only_its_own_days(self):
        result = reconcile([compensated("2026-09-26", "2026-10-09", 0)], overtime_on(("2026-10-09", "08:00", "10:00"), ("2026-10-10", "09:00", "12:00")))
        self.assertEqual(result.periods[0].shortfall, timedelta())
        self.assertEqual([d.date for d in result.unmatched], [date(2026, 10, 10)])

    def test_unpaid_overtime_shows_as_a_shortfall(self):
        result = reconcile([compensated("2026-10-01", "2026-10-31", 1), compensated("2026-10-01", "2026-10-31", 0.5, "time_off")],
                           overtime_on(("2026-10-05", "08:00", "19:00")))
        self.assertEqual(result.shortfall, timedelta(hours=1, minutes=30))



class EachLabelIsCompensatedForItsOwnOvertime(unittest.TestCase):
    weeks_per_label = {"Northwind": overtime_on(("2026-10-05", "08:00", "19:00")), "Acme": overtime_on(("2026-10-11", "09:00", "11:00"))}

    def test_compensation_from_one_label_never_covers_another(self):
        result = reconcile_by_label([compensated("2026-10-01", "2026-10-31", 3, label="Acme")], self.weeks_per_label, "Northwind")
        self.assertEqual((result["Northwind"].compensated, result["Northwind"].unmatched_overtime), (timedelta(), timedelta(hours=3)))
        self.assertEqual((result["Acme"].owed, result["Acme"].compensated), (timedelta(hours=2), timedelta(hours=3)))

    def test_compensation_without_a_label_belongs_to_the_default(self):
        result = reconcile_by_label([compensated("2026-10-01", "2026-10-31", 3)], self.weeks_per_label, "Northwind")
        self.assertEqual((result["Northwind"].shortfall, list(result)), (timedelta(), ["Northwind", "Acme"]))

    def test_the_totals_add_up_every_label(self):
        everything = all_labels(reconcile_by_label([compensated("2026-10-01", "2026-10-31", 1, label="Acme")], self.weeks_per_label, "Northwind"))
        self.assertEqual((everything.owed, everything.compensated, everything.shortfall), (timedelta(hours=5), timedelta(hours=1), timedelta(hours=1)))


if __name__ == "__main__":
    unittest.main()
