import unittest
from datetime import time, timedelta

from chronata.presenters.text.text_report import punctuality
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.overtime import combined, days_so_far, weeks, weeks_by_label
from chronata.timekeeping.hours.working_day import Lunch, WorkingDay
from chronata.timekeeping.shifts.shifts import Shift
from tests.fakes import at


def working_day(workdays: range = range(5)) -> WorkingDay:
    return WorkingDay(time(8), time(17), Lunch(time(12), 60), frozenset(workdays), weekly_limit=40)


def shift(day: str, start: str, end: str | None, label: str = "") -> Shift:
    return Shift(1, at(f"{day}T{start}"), at(f"{day}T{end}") if end else None, timedelta(), label)


def split_day(day: str, start: str, end: str) -> list[Shift]:
    return [shift(day, start, "12:00"), shift(day, "13:00", end)]


def only_day(shifts: list[Shift]):
    return weeks(shifts, working_day())[0].days[0]


class FullDay(unittest.TestCase):
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


class LabelsWithTheirOwnHours(unittest.TestCase):
    hours = LabelHours("Northwind", {"Northwind": WorkingDay(time(8), time(17), Lunch(time(12), 60)), "Acme": None})

    def test_a_label_with_no_set_hours_only_counts_time(self):
        day = weeks([shift("2026-10-05", "18:00", "23:00", "Acme")], None)[0].days[0]
        self.assertEqual((day.worked, day.overtime, day.late, day.short), (timedelta(hours=5), timedelta(), timedelta(), timedelta()))

    def test_evening_side_work_is_not_overtime_for_the_main_job(self):
        by_label = weeks_by_label(split_day("2026-10-05", "08:00", "17:00") + [shift("2026-10-05", "18:00", "21:00", "Acme")], self.hours)
        self.assertEqual({label: w[0].overtime for label, w in by_label.items()}, {"Northwind": timedelta(), "Acme": timedelta()})
        whole = combined(by_label, "Northwind")[0].days[0]
        self.assertEqual((whole.worked, whole.overtime), (timedelta(hours=11), timedelta()))

    def test_unlabelled_time_counts_as_the_default_labels(self):
        self.assertEqual(list(weeks_by_label([shift("2026-10-05", "08:00", "12:00")], self.hours)), ["Northwind"])


class MakingUpALateStart(unittest.TestCase):
    hours = LabelHours("Northwind", {"Northwind": WorkingDay(time(8, 30), time(17, 30), Lunch(time(12), 60))})

    def today_at(self, moment: str, *pieces: tuple[str, str | None]):
        shifts = [shift("2026-10-15", start, end, "Northwind") for start, end in pieces]
        return days_so_far(shifts, self.hours, at(f"2026-10-15T{moment}"))[(at("2026-10-15T00:00:00").date(), "Northwind")]

    def test_ten_minutes_late_is_made_up_by_going_to_lunch_ten_minutes_later(self):
        day = self.today_at("12:30:00", ("08:40", "12:10"))
        self.assertEqual((day.late, day.made_up, day.running, punctuality(day)), (timedelta(minutes=10), True, True, "arrived 0:10 late, made up so far"))

    def test_going_to_lunch_on_time_leaves_it_behind_so_far(self):
        day = self.today_at("12:30:00", ("08:40", "12:00"))
        self.assertEqual(punctuality(day), "arrived 0:10 late, 0:10 behind so far")

    def test_while_still_working_it_is_measured_up_to_now(self):
        day = self.today_at("10:00:00", ("08:40", None))
        self.assertEqual((day.worked, day.short, day.running), (timedelta(hours=1, minutes=20), timedelta(minutes=10), True))

    def test_leaving_early_is_behind_so_far_until_the_shift_time_is_over_then_short(self):
        pieces = (("08:40", "12:10"), ("13:10", "15:00"))
        self.assertEqual(punctuality(self.today_at("16:00:00", *pieces)), "arrived 0:10 late, 0:10 behind so far")
        self.assertEqual(punctuality(self.today_at("18:00:00", *pieces)), "arrived 0:10 late, 2:40 short of a full day")

    def test_overtime_only_starts_once_the_late_start_is_made_up(self):
        lunch = ("08:40", "12:10")
        self.assertEqual(self.today_at("20:00:00", lunch, ("13:10", "17:40")).overtime, timedelta())
        self.assertEqual(self.today_at("20:00:00", lunch, ("13:10", "17:50")).overtime, timedelta(minutes=10))

    def test_a_full_day_after_a_late_start_is_made_up_once_the_day_is_over(self):
        day = self.today_at("18:00:00", ("08:40", "12:10"), ("13:10", "17:40"))
        self.assertEqual((day.made_up, day.running), (True, False))


if __name__ == "__main__":
    unittest.main()
