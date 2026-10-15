import unittest
from datetime import time, timedelta

from chronata.timekeeping.shifts import Shift
from chronata.timekeeping.working_day import WorkingDay, check_fits, weeks
from chronata.timekeeping.labels import worked_by_label
from tests.fakes import at


def working_day(workdays: range = range(5)) -> WorkingDay:
    return WorkingDay(time(8), time(17), time(12), 60, frozenset(workdays), 40, True)


def shift(day: str, start: str, end: str, label: str = "") -> Shift:
    return Shift(1, at(f"{day}T{start}"), at(f"{day}T{end}"), timedelta(), label)


def split_day(day: str, start: str, end: str) -> list[Shift]:
    return [shift(day, start, "12:00"), shift(day, "13:00", end)]


def only_day(shifts: list[Shift]):
    return weeks(shifts, working_day())[0].days[0]


class FullDay(unittest.TestCase):
    def test_a_full_day_is_the_shift_less_lunch(self):
        self.assertEqual(working_day().daily_hours, 8)

    def test_working_through_lunch_counts_as_overtime(self):
        day = only_day([shift("2026-10-05", "08:00", "17:00")])
        self.assertEqual((day.worked, day.overtime), (timedelta(hours=9), timedelta(hours=1)))

    def test_clocking_out_for_lunch_makes_a_normal_day(self):
        day = only_day(split_day("2026-10-05", "08:00", "17:00"))
        self.assertEqual((day.worked, day.overtime), (timedelta(hours=8), timedelta()))

    def test_every_hour_on_a_day_off_is_overtime(self):
        self.assertEqual(only_day([shift("2026-10-11", "10:00", "14:00")]).overtime, timedelta(hours=4))

    def test_hours_past_the_weekly_limit_are_overtime_even_within_daily_limits(self):
        six_days = [shift(f"2026-10-{d:02d}", "08:00", "16:00") for d in range(5, 11)]
        self.assertEqual(weeks(six_days, working_day(workdays=range(6)))[0].overtime, timedelta(hours=8))

    def test_an_hour_is_never_counted_twice(self):
        long_days = [shift(f"2026-10-{d:02d}", "08:00", "18:00") for d in range(5, 10)]
        self.assertEqual(weeks(long_days, working_day())[0].overtime, timedelta(hours=10))


class Lateness(unittest.TestCase):
    def test_a_minute_late_and_a_minute_later_out_is_made_up_without_overtime(self):
        day = only_day(split_day("2026-10-05", "08:01", "17:01"))
        self.assertEqual((day.late, day.made_up, day.overtime), (timedelta(minutes=1), True, timedelta()))

    def test_staying_well_past_making_it_up_is_overtime(self):
        day = only_day(split_day("2026-10-05", "08:01", "18:40"))
        self.assertEqual((day.made_up, day.overtime), (True, timedelta(minutes=99)))

    def test_leaving_on_time_after_arriving_late_is_short(self):
        day = only_day(split_day("2026-10-05", "08:03", "17:00"))
        self.assertEqual((day.short, day.made_up), (timedelta(minutes=3), False))


class EarlyLeaving(unittest.TestCase):
    def test_up_to_seven_minutes_early_after_arriving_on_time_is_a_full_day(self):
        day = only_day(split_day("2026-10-05", "07:59", "16:53"))
        self.assertEqual((day.short, day.worked), (timedelta(), timedelta(hours=7, minutes=54)))

    def test_ten_minutes_early_is_short(self):
        self.assertEqual(only_day(split_day("2026-10-05", "08:00", "16:50")).short, timedelta(minutes=10))

    def test_leaving_early_after_arriving_late_is_not_forgiven(self):
        day = only_day(split_day("2026-10-05", "08:03", "16:57"))
        self.assertEqual((day.short, day.made_up), (timedelta(minutes=6), False))


class WorkdayBoundaries(unittest.TestCase):
    def test_only_a_clock_out_before_the_end_of_a_workday_needs_asking(self):
        self.assertTrue(working_day().before_end_of_workday(at("2026-10-14T14:20:00")))
        self.assertFalse(working_day().before_end_of_workday(at("2026-10-14T17:00:00")))
        self.assertFalse(working_day().before_end_of_workday(at("2026-10-17T14:20:00")))

    def test_a_shift_and_lunch_that_do_not_fit_are_refused(self):
        with self.assertRaises(ValueError):
            check_fits(time(17), time(8), time(12), 60)
        with self.assertRaises(ValueError):
            check_fits(time(8), time(17), time(18), 60)


class Labels(unittest.TestCase):
    def test_hours_are_totalled_per_label(self):
        totals = worked_by_label([shift("2026-10-05", "08:00", "12:00", "Acme"), shift("2026-10-05", "13:00", "15:00", "Globex"),
                                  shift("2026-10-06", "08:00", "09:00", "Acme")])
        self.assertEqual(totals, {"Acme": timedelta(hours=5), "Globex": timedelta(hours=2)})


if __name__ == "__main__":
    unittest.main()
