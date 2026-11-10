import unittest
from datetime import time, timedelta

from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.lateness_made_up import lateness_made_up_by
from chronata.timekeeping.hours.working_day import Lunch, WorkingDay
from chronata.timekeeping.shifts.shifts import WAIVED, Break, Shift
from tests.fakes import at

DAY = "2026-10-05"
EIGHT_HOURS = LabelHours("", {"": WorkingDay(time(8), time(17), Lunch(time(12), 60), frozenset(range(5)), weekly_limit=40)})


def shift(shift_id: int, start: str, end: str | None) -> Shift:
    ended = None
    if end is not None:
        ended = at(f"{DAY}T{end}")
    return Shift(shift_id, at(f"{DAY}T{start}"), ended, timedelta())


def made_up(shifts: list[Shift], waived_from: str, waived_to: str, now: str = "23:00") -> timedelta:
    stretch = Break(at(f"{DAY}T{waived_from}"), at(f"{DAY}T{waived_to}"), WAIVED, "not working")
    return lateness_made_up_by(stretch, shifts[-1], shifts, EIGHT_HOURS, at(f"{DAY}T{now}"))


class LatenessMadeUpByAStretch(unittest.TestCase):
    def test_is_how_much_of_it_the_day_needs_to_cover_the_late_start(self):
        self.assertEqual(made_up([shift(1, "08:30", "19:00")], "16:00", "19:00"), timedelta(minutes=30))

    def test_is_nothing_when_the_rest_of_the_day_already_covers_it(self):
        self.assertEqual(made_up([shift(1, "08:30", "19:00")], "17:00", "19:00"), timedelta())

    def test_is_nothing_when_the_day_started_on_time(self):
        self.assertEqual(made_up([shift(1, "08:00", "19:00")], "15:00", "19:00"), timedelta())

    def test_is_nothing_while_the_shift_is_still_clocked_in(self):
        self.assertEqual(made_up([shift(1, "08:30", None)], "16:00", "19:00", now="19:00"), timedelta())

    def test_is_nothing_when_the_day_is_short_by_more_than_the_lateness(self):
        shifts = [shift(1, "08:30", "12:00"), shift(2, "14:00", "16:30")]
        self.assertEqual(made_up(shifts, "15:00", "16:30"), timedelta())

    def test_covers_only_what_the_day_already_covered_when_it_was_partly_short(self):
        self.assertEqual(made_up([shift(1, "08:30", "16:20")], "16:00", "16:20"), timedelta(minutes=20))


if __name__ == "__main__":
    unittest.main()
