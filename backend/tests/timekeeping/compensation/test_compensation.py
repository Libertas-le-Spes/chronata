import unittest
from datetime import date, datetime, time, timedelta

from chronata.timekeeping.compensation.compensation import all_labels, compensations, reconcile, reconcile_by_label
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.record.record import Entry
from chronata.timekeeping.shifts.shifts import Shift
from tests.fakes import SAST, at
from tests.one_label import weeks

NO_LUNCH = WorkingDay(time(8), time(16))
PRIMARY_FIRST = LabelHours("Primary")


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



class LatenessComesOffTheUncompensatedTotal(unittest.TestCase):
    def test_lateness_not_covered_is_taken_off_overtime_with_no_compensation_yet(self):
        worked = overtime_on(("2026-10-05", "08:00", "18:00"), ("2026-10-06", "08:20", "16:00"))
        result = reconcile([], worked)
        self.assertEqual((result.uncovered_lateness, result.unpaid), (timedelta(minutes=20), timedelta(hours=1, minutes=40)))

    def test_lateness_is_taken_off_what_recorded_periods_left_uncompensated(self):
        worked = overtime_on(("2026-10-05", "08:00", "19:00"), ("2026-10-06", "08:30", "16:00"))
        result = reconcile(compensations([compensated("2026-10-01", "2026-10-31", 1)]), worked)
        self.assertEqual((result.shortfall, result.unpaid), (timedelta(hours=2), timedelta(hours=1, minutes=30)))

    def test_only_days_with_lateness_left_uncovered_are_listed(self):
        result = reconcile([], overtime_on(("2026-10-05", "08:00", "16:00"), ("2026-10-06", "08:20", "16:00"), ("2026-10-07", "08:10", "16:30")))
        self.assertEqual([late.date for late in result.lateness], [date(2026, 10, 6)])

    def test_lateness_a_weekly_limit_already_absorbed_is_not_taken_off_again(self):
        weekly_limit = WorkingDay(time(8), time(16), weekly_limit=32)
        late_monday = Shift(1, at("2026-10-05T08:10:00"), at("2026-10-05T16:00:00"), timedelta())
        tuesday = Shift(2, at("2026-10-06T08:00:00"), at("2026-10-06T16:00:00"), timedelta())
        wednesday = Shift(3, at("2026-10-07T08:00:00"), at("2026-10-07T16:00:00"), timedelta())
        thursday = Shift(4, at("2026-10-08T08:00:00"), at("2026-10-08T16:00:00"), timedelta())
        friday = Shift(5, at("2026-10-09T08:00:00"), at("2026-10-09T16:00:00"), timedelta())
        worked = weeks([late_monday, tuesday, wednesday, thursday, friday], weekly_limit)
        result = reconcile([], worked)
        self.assertEqual((result.unmatched_overtime.earned, result.uncovered_lateness, result.unpaid),
                         (timedelta(hours=7, minutes=50), timedelta(), timedelta(hours=7, minutes=50)))

    def test_a_week_with_room_left_takes_the_lateness_off(self):
        worked = overtime_on(("2026-10-05", "08:10", "16:00"), ("2026-10-06", "08:00", "18:00"))
        self.assertEqual(reconcile([], worked).unpaid, timedelta(hours=1, minutes=50))

    def test_an_overpaid_period_still_leaves_a_total_that_adds_up(self):
        worked = overtime_on(("2026-10-05", "08:00", "18:00"), ("2026-10-06", "08:20", "16:00"), ("2026-10-12", "08:00", "11:00"))
        result = reconcile(compensations([compensated("2026-10-01", "2026-10-07", 5)]), worked)
        self.assertEqual(result.owed.earned - result.compensated - result.uncovered_lateness, result.unpaid)
        self.assertEqual(result.beyond_owed, timedelta(hours=3))

    def test_more_lateness_than_overtime_goes_below_zero(self):
        result = reconcile([], overtime_on(("2026-10-05", "08:00", "16:10"), ("2026-10-06", "08:30", "16:00")))
        self.assertEqual(result.unpaid, timedelta(minutes=-20))

    def test_every_labels_lateness_is_in_the_totals(self):
        weeks_per_label = {"Primary": overtime_on(("2026-10-05", "08:15", "16:00")), "Secondary": overtime_on(("2026-10-06", "08:05", "16:00"))}
        everything = all_labels(reconcile_by_label([], weeks_per_label, PRIMARY_FIRST))
        self.assertEqual(everything.uncovered_lateness, timedelta(minutes=20))


class EachLabelIsCompensatedForItsOwnOvertime(unittest.TestCase):
    weeks_per_label = {"Primary": overtime_on(("2026-10-05", "08:00", "19:00")), "Secondary": overtime_on(("2026-10-11", "09:00", "11:00"))}

    def test_compensation_from_one_label_never_covers_another(self):
        result = reconcile_by_label([compensated("2026-10-01", "2026-10-31", 3, label="Secondary")], self.weeks_per_label, PRIMARY_FIRST)
        self.assertEqual((result["Primary"].compensated, result["Primary"].unmatched_overtime.earned), (timedelta(), timedelta(hours=3)))
        self.assertEqual((result["Secondary"].owed.earned, result["Secondary"].compensated, result["Secondary"].beyond_owed),
                         (timedelta(hours=2), timedelta(hours=2), timedelta(hours=1)))

    def test_compensation_without_a_label_belongs_to_the_default(self):
        result = reconcile_by_label([compensated("2026-10-01", "2026-10-31", 3)], self.weeks_per_label, PRIMARY_FIRST)
        self.assertEqual((result["Primary"].shortfall, list(result)), (timedelta(), ["Primary", "Secondary"]))

    def test_labels_after_the_default_are_in_the_same_order_every_time(self):
        weeks_per_label = {}
        for spelling in ("secondary", "sEcondary", "SECONDARY", "Secondary", "secondarY"):
            weeks_per_label[spelling] = overtime_on(("2026-10-11", "09:00", "10:00"))
        self.assertEqual(list(reconcile_by_label([], weeks_per_label, PRIMARY_FIRST)), ["SECONDARY", "Secondary", "sEcondary", "secondarY", "secondary"])

    def test_the_totals_add_up_every_label(self):
        everything = all_labels(reconcile_by_label([compensated("2026-10-01", "2026-10-31", 1, label="Secondary")], self.weeks_per_label, PRIMARY_FIRST))
        self.assertEqual((everything.owed.earned, everything.compensated, everything.shortfall), (timedelta(hours=5), timedelta(hours=1), timedelta(hours=1)))


if __name__ == "__main__":
    unittest.main()
