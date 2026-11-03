import unittest
from datetime import datetime, time, timedelta

from chronata.presenters.text.text_report import punctuality
from chronata.timekeeping.hours.all_labels import combined
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.timesheet import days_so_far, weeks_by_label
from chronata.timekeeping.hours.working_day import Lunch, WorkingDay
from chronata.timekeeping.shifts.shifts import Shift
from chronata.timekeeping.shifts.start_answer import StartAnswer
from tests.fakes import at
from tests.one_label import weeks


def working_day(workdays: range = range(5)) -> WorkingDay:
    return WorkingDay(time(8), time(17), Lunch(time(12), 60), frozenset(workdays), weekly_limit=40)


def shift(day: str, start: str, end: str | None, label: str = "") -> Shift:
    return Shift(1, at(f"{day}T{start}"), _ended(day, end), timedelta(), label)


def _ended(day: str, end: str | None) -> datetime | None:
    if end is None:
        return None
    return at(f"{day}T{end}")


def split_day(day: str, start: str, end: str) -> list[Shift]:
    return [shift(day, start, "12:00"), shift(day, "13:00", end)]


def only_day(shifts: list[Shift]):
    return weeks(shifts, working_day())[0].days[0]


class FullDay(unittest.TestCase):
    def test_working_through_lunch_counts_as_overtime(self):
        day = only_day([shift("2026-10-05", "08:00", "17:00")])
        self.assertEqual((day.worked, day.overtime.earned), (timedelta(hours=9), timedelta(hours=1)))

    def test_clocking_out_for_lunch_makes_a_normal_day(self):
        day = only_day(split_day("2026-10-05", "08:00", "17:00"))
        self.assertEqual((day.worked, day.overtime.earned), (timedelta(hours=8), timedelta()))

    def test_every_hour_on_a_day_off_is_overtime(self):
        self.assertEqual(only_day([shift("2026-10-11", "10:00", "14:00")]).overtime.earned, timedelta(hours=4))

    def test_hours_past_the_weekly_limit_are_overtime_even_within_daily_limits(self):
        six_days = [shift(f"2026-10-{d:02d}", "08:00", "16:00") for d in range(5, 11)]
        self.assertEqual(weeks(six_days, working_day(workdays=range(6)))[0].overtime.earned, timedelta(hours=8))

    def test_an_hour_is_never_counted_twice(self):
        long_days = [shift(f"2026-10-{d:02d}", "08:00", "18:00") for d in range(5, 10)]
        self.assertEqual(weeks(long_days, working_day())[0].overtime.earned, timedelta(hours=10))


class Lateness(unittest.TestCase):
    def test_a_minute_late_and_a_minute_later_out_is_made_up_without_overtime(self):
        day = only_day(split_day("2026-10-05", "08:01", "17:01"))
        self.assertEqual((day.punctuality.late, day.punctuality.made_up, day.overtime.earned), (timedelta(minutes=1), True, timedelta()))

    def test_staying_well_past_making_it_up_is_overtime(self):
        day = only_day(split_day("2026-10-05", "08:01", "18:40"))
        self.assertEqual((day.punctuality.made_up, day.overtime.earned), (True, timedelta(minutes=99)))

    def test_leaving_on_time_after_arriving_late_is_short(self):
        day = only_day(split_day("2026-10-05", "08:03", "17:00"))
        self.assertEqual((day.punctuality.short, day.punctuality.made_up), (timedelta(minutes=3), False))


class EarlyLeaving(unittest.TestCase):
    def test_up_to_seven_minutes_early_after_arriving_on_time_is_a_full_day(self):
        day = only_day(split_day("2026-10-05", "07:59", "16:53"))
        self.assertEqual((day.punctuality.short, day.worked), (timedelta(), timedelta(hours=7, minutes=54)))

    def test_ten_minutes_early_is_short(self):
        self.assertEqual(only_day(split_day("2026-10-05", "08:00", "16:50")).punctuality.short, timedelta(minutes=10))

    def test_leaving_early_after_arriving_late_is_not_forgiven(self):
        day = only_day(split_day("2026-10-05", "08:03", "16:57"))
        self.assertEqual((day.punctuality.short, day.punctuality.made_up), (timedelta(minutes=6), False))


class LabelsWithTheirOwnHours(unittest.TestCase):
    hours = LabelHours("Primary", {"Primary": WorkingDay(time(8), time(17), Lunch(time(12), 60)), "Secondary": None})

    def test_a_label_with_no_set_hours_only_counts_time(self):
        day = weeks([shift("2026-10-05", "18:00", "23:00", "Secondary")], None)[0].days[0]
        self.assertEqual((day.worked, day.overtime.earned, day.punctuality.late, day.punctuality.short), (timedelta(hours=5), timedelta(), timedelta(), timedelta()))

    def test_evening_side_work_is_not_overtime_for_the_main_job(self):
        by_label = weeks_by_label(split_day("2026-10-05", "08:00", "17:00") + [shift("2026-10-05", "18:00", "21:00", "Secondary")], self.hours)
        self.assertEqual({label: w[0].overtime.earned for label, w in by_label.items()}, {"Primary": timedelta(), "Secondary": timedelta()})
        whole = combined(by_label, "Primary")[0].days[0]
        self.assertEqual((whole.worked, whole.overtime.earned), (timedelta(hours=11), timedelta()))

    def test_a_day_on_two_labels_runs_from_the_first_clock_in_to_the_last_clock_out(self):
        by_label = weeks_by_label(split_day("2026-10-05", "08:00", "17:00") + [shift("2026-10-05", "18:00", "21:00", "Secondary")], self.hours)
        whole = combined(by_label, "Primary")[0].days[0]
        self.assertEqual((whole.first_in, whole.last_out), (at("2026-10-05T08:00:00"), at("2026-10-05T21:00:00")))

    def test_a_day_on_two_labels_is_running_while_the_main_label_is_clocked_in(self):
        shifts = [shift("2026-10-05", "06:00", "07:00", "Secondary"), shift("2026-10-05", "08:00", None, "Primary")]
        whole = combined(weeks_by_label(shifts, self.hours, at("2026-10-05T10:00:00")), "Primary")[0].days[0]
        self.assertTrue(whole.running)

    def test_a_day_on_two_labels_is_running_while_only_the_other_label_is_clocked_in(self):
        both_with_hours = LabelHours("Primary", {"Primary": WorkingDay(time(8), time(17), Lunch(time(12), 60)), "Secondary": WorkingDay(time(18), time(22))})
        shifts = split_day("2026-10-05", "08:00", "17:00") + [shift("2026-10-05", "18:00", None, "Secondary")]
        whole = combined(weeks_by_label(shifts, both_with_hours, at("2026-10-05T19:00:00")), "Primary")[0].days[0]
        self.assertTrue(whole.running)

    def test_unlabelled_time_counts_as_the_default_labels(self):
        self.assertEqual(list(weeks_by_label([shift("2026-10-05", "08:00", "12:00")], self.hours)), ["Primary"])


def answered(piece: Shift, answer: StartAnswer) -> Shift:
    piece.start_answer = answer
    return piece


class LatenessOnASecondLabel(unittest.TestCase):
    hours = LabelHours("Primary", {"Primary": WorkingDay(time(8), time(12)), "Secondary": WorkingDay(time(8), time(17))})

    def secondary_day(self, answer: StartAnswer):
        pieces = [shift("2026-10-05", "07:00", "08:00", "Primary"), answered(shift("2026-10-05", "13:00", "17:00", "Secondary"), answer)]
        return weeks_by_label(pieces, self.hours)["Secondary"][0].days[0]

    def test_starting_a_different_project_later_in_the_day_is_not_late(self):
        self.assertEqual(self.secondary_day(StartAnswer(late=False, label="Secondary")).punctuality.late, timedelta())

    def test_saying_you_are_late_for_it_counts_the_lateness(self):
        self.assertEqual(self.secondary_day(StartAnswer(late=True, label="Secondary")).punctuality.late, timedelta(hours=5))

    def test_a_late_answer_on_a_shift_that_starts_after_its_hours_does_not_count(self):
        evening = answered(shift("2026-10-05", "18:00", "19:00", "Secondary"), StartAnswer(late=True, label="Secondary"))
        pieces = [shift("2026-10-05", "07:00", "08:00", "Primary"), evening]
        self.assertEqual(weeks_by_label(pieces, self.hours)["Secondary"][0].days[0].punctuality.late, timedelta())

    def test_a_late_answer_for_another_label_does_not_follow_a_relabelled_shift(self):
        relabelled = answered(shift("2026-10-05", "13:00", "17:00", "Tertiary"), StartAnswer(late=True, label="Secondary"))
        hours = LabelHours("Primary", {"Primary": WorkingDay(time(8), time(12)), "Tertiary": WorkingDay(time(8), time(17))})
        pieces = [shift("2026-10-05", "07:00", "08:00", "Primary"), relabelled]
        self.assertEqual(weeks_by_label(pieces, hours)["Tertiary"][0].days[0].punctuality.late, timedelta())

    def test_the_label_you_clocked_in_on_first_counts_its_lateness_without_asking(self):
        pieces = [shift("2026-10-05", "08:20", "12:00", "Primary"), shift("2026-10-05", "13:00", "17:00", "Secondary")]
        self.assertEqual(weeks_by_label(pieces, self.hours)["Primary"][0].days[0].punctuality.late, timedelta(minutes=20))


class StartingAfterTheShiftEnded(unittest.TestCase):
    def evening(self, answer: StartAnswer):
        return only_day([answered(shift("2026-10-05", "18:00", "20:00"), answer)])

    def test_normal_hours_after_the_shift_are_not_counted_as_late(self):
        day = self.evening(StartAnswer(overtime_after_shift=False, label=""))
        self.assertEqual((day.punctuality.late, day.punctuality.started_after_shift), (timedelta(), True))

    def test_a_start_after_the_shift_is_listed_to_check(self):
        self.assertIn("started after the shift ended", punctuality(self.evening(StartAnswer())))

    def test_overtime_after_the_shift_is_still_marked_to_check(self):
        self.assertTrue(self.evening(StartAnswer(overtime_after_shift=True, label="")).punctuality.started_after_shift)

    def test_a_later_label_after_its_shift_is_not_marked_when_nothing_was_asked(self):
        both = LabelHours("Primary", {"Primary": WorkingDay(time(8), time(17)), "Secondary": WorkingDay(time(8), time(16))})
        pieces = [shift("2026-10-05", "08:00", "17:00", "Primary"), shift("2026-10-05", "17:00", "18:00", "Secondary")]
        self.assertFalse(weeks_by_label(pieces, both)["Secondary"][0].days[0].punctuality.started_after_shift)

    def test_overtime_after_the_shift_counts_every_hour_as_overtime(self):
        self.assertEqual(self.evening(StartAnswer(overtime_after_shift=True, label="")).overtime.earned, timedelta(hours=2))


class MakingUpALateStart(unittest.TestCase):
    hours = LabelHours("Primary", {"Primary": WorkingDay(time(8, 30), time(17, 30), Lunch(time(12), 60))})

    def today_at(self, moment: str, *pieces: tuple[str, str | None]):
        shifts = [shift("2026-10-15", start, end, "Primary") for start, end in pieces]
        return days_so_far(shifts, self.hours, at(f"2026-10-15T{moment}"))[(at("2026-10-15T00:00:00").date(), "Primary")]

    def test_ten_minutes_late_is_made_up_by_going_to_lunch_ten_minutes_later(self):
        day = self.today_at("12:30:00", ("08:40", "12:10"))
        self.assertEqual((day.punctuality.late, day.punctuality.made_up, day.running, punctuality(day)), (timedelta(minutes=10), True, True, "arrived 0:10 late, made up so far"))

    def test_going_to_lunch_on_time_leaves_it_behind_so_far(self):
        day = self.today_at("12:30:00", ("08:40", "12:00"))
        self.assertEqual(punctuality(day), "arrived 0:10 late, 0:10 behind so far")

    def test_while_still_working_it_is_measured_up_to_now(self):
        day = self.today_at("10:00:00", ("08:40", None))
        self.assertEqual((day.worked, day.punctuality.short, day.running), (timedelta(hours=1, minutes=20), timedelta(minutes=10), True))

    def test_leaving_early_is_behind_so_far_until_the_shift_time_is_over_then_short(self):
        pieces = (("08:40", "12:10"), ("13:10", "15:00"))
        self.assertEqual(punctuality(self.today_at("16:00:00", *pieces)), "arrived 0:10 late, 0:10 behind so far")
        self.assertEqual(punctuality(self.today_at("18:00:00", *pieces)), "arrived 0:10 late, 2:40 short of a full day")

    def test_overtime_only_starts_once_the_late_start_is_made_up(self):
        lunch = ("08:40", "12:10")
        self.assertEqual(self.today_at("20:00:00", lunch, ("13:10", "17:40")).overtime.earned, timedelta())
        self.assertEqual(self.today_at("20:00:00", lunch, ("13:10", "17:50")).overtime.earned, timedelta(minutes=10))

    def test_while_clocked_in_on_a_day_off_it_is_still_running(self):
        saturday = shift("2026-10-17", "09:00", None, "Primary")
        day = days_so_far([saturday], self.hours, at("2026-10-17T11:00:00"))[(at("2026-10-17T00:00:00").date(), "Primary")]
        self.assertEqual((day.running, day.overtime.earned), (True, timedelta(hours=2)))

    def test_lateness_is_not_taken_off_while_the_day_is_still_running(self):
        day = self.today_at("12:30:00", ("08:40", "12:00"))
        self.assertEqual((day.punctuality.uncovered_lateness, day.uncovered_lateness), (timedelta(minutes=10), timedelta()))

    def test_lateness_left_uncovered_is_taken_off_once_the_day_is_over(self):
        day = self.today_at("18:00:00", ("08:40", "12:10"), ("13:10", "17:35"))
        self.assertEqual(day.uncovered_lateness, timedelta(minutes=5))

    def test_a_full_day_after_a_late_start_is_made_up_once_the_day_is_over(self):
        day = self.today_at("18:00:00", ("08:40", "12:10"), ("13:10", "17:40"))
        self.assertEqual((day.punctuality.made_up, day.running), (True, False))


if __name__ == "__main__":
    unittest.main()
