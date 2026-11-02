import unittest
from datetime import date, datetime, time, timedelta

from chronata.timekeeping.compensation.compensation import all_labels, compensations, reconcile, reconcile_by_label
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.timesheet import weeks
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.record.record import Entry
from chronata.timekeeping.shifts.shifts import Shift
from tests.fakes import SAST, at

NO_LUNCH = WorkingDay(time(8), time(16))
NORTHWIND_FIRST = LabelHours("Northwind")


def overtime_on(*days: tuple[str, str, str]):
    return weeks([Shift(1, at(f"{d}T{s}"), at(f"{d}T{e}"), timedelta()) for d, s, e in days], NO_LUNCH)


def compensated(start: str, end: str, hours: float, kind: str = "paid", label: str = "", reference: str = "") -> Entry:
    data = {"from": start, "to": end, "hours": hours, "kind": kind}
    if label:
        data["label"] = label
    if reference:
        data["reference"] = reference
    return Entry(1, "compensation", datetime.now(SAST), data)


class Reconciling(unittest.TestCase):
    def test_a_period_takes_its_first_and_last_days_and_nothing_after(self):
        worked = overtime_on(("2026-09-26", "09:00", "10:00"), ("2026-10-09", "08:00", "18:00"), ("2026-10-10", "09:00", "12:00"))
        result = reconcile(compensations([compensated("2026-09-26", "2026-10-09", 0)]), worked)
        self.assertEqual(result.periods[0].owed.earned, timedelta(hours=3))
        self.assertEqual([d.date for d in result.unmatched], [date(2026, 10, 10)])

    def test_unpaid_overtime_shows_as_a_shortfall(self):
        result = reconcile(compensations([compensated("2026-10-01", "2026-10-31", 1), compensated("2026-10-01", "2026-10-31", 0.5, "time_off")]),
                           overtime_on(("2026-10-05", "08:00", "19:00")))
        self.assertEqual(result.shortfall, timedelta(hours=1, minutes=30))

    def test_a_kind_of_compensation_this_version_does_not_know_counts_as_neither_but_keeps_its_reference(self):
        records = compensations([compensated("2026-10-01", "2026-10-31", 0.5, "time_off"), compensated("2026-10-01", "2026-10-31", 1, "bonus", reference="note 4")])
        period = reconcile(records, overtime_on(("2026-10-05", "08:00", "18:00"))).periods[0]
        self.assertEqual((period.paid, period.time_off, period.references), (timedelta(), timedelta(minutes=30), ("note 4",)))



class EachLabelIsCompensatedForItsOwnOvertime(unittest.TestCase):
    weeks_per_label = {"Northwind": overtime_on(("2026-10-05", "08:00", "19:00")), "Acme": overtime_on(("2026-10-11", "09:00", "11:00"))}

    def test_compensation_from_one_label_never_covers_another(self):
        result = reconcile_by_label([compensated("2026-10-01", "2026-10-31", 3, label="Acme")], self.weeks_per_label, NORTHWIND_FIRST)
        self.assertEqual((result["Northwind"].compensated, result["Northwind"].unmatched_overtime.earned), (timedelta(), timedelta(hours=3)))
        self.assertEqual((result["Acme"].owed.earned, result["Acme"].compensated), (timedelta(hours=2), timedelta(hours=3)))

    def test_compensation_without_a_label_belongs_to_the_default(self):
        result = reconcile_by_label([compensated("2026-10-01", "2026-10-31", 3)], self.weeks_per_label, NORTHWIND_FIRST)
        self.assertEqual((result["Northwind"].shortfall, list(result)), (timedelta(), ["Northwind", "Acme"]))

    def test_labels_after_the_default_are_in_the_same_order_every_time(self):
        weeks_per_label = {"acme": overtime_on(("2026-10-11", "09:00", "10:00")), "Acme": overtime_on(("2026-10-11", "09:00", "11:00"))}
        self.assertEqual(list(reconcile_by_label([], weeks_per_label, NORTHWIND_FIRST)), ["Acme", "acme"])

    def test_the_totals_add_up_every_label(self):
        everything = all_labels(reconcile_by_label([compensated("2026-10-01", "2026-10-31", 1, label="Acme")], self.weeks_per_label, NORTHWIND_FIRST))
        self.assertEqual((everything.owed.earned, everything.compensated, everything.shortfall), (timedelta(hours=5), timedelta(hours=1), timedelta(hours=1)))


if __name__ == "__main__":
    unittest.main()
