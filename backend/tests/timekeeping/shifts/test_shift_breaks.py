import unittest
from datetime import timedelta

from chronata.timekeeping.shifts.shifts import CLOCKED_OUT, WAIVED, Break, Shift
from tests.fakes import at


def day_shift() -> Shift:
    return Shift(1, at("2026-10-14T08:00:00"), at("2026-10-14T20:00:00"), timedelta())


class BreaksInAShift(unittest.TestCase):
    def test_a_break_added_out_of_order_is_kept_in_time_order(self):
        shift = day_shift()
        shift.add_break(Break(at("2026-10-14T15:00:00"), at("2026-10-14T16:00:00"), CLOCKED_OUT))
        shift.add_break(Break(at("2026-10-14T10:00:00"), at("2026-10-14T11:00:00"), WAIVED, "away"))
        self.assertEqual(shift.worked(shift.end), timedelta(hours=10))

    def test_overlapping_breaks_are_not_taken_off_twice(self):
        shift = day_shift()
        shift.add_break(Break(at("2026-10-14T12:00:00"), at("2026-10-14T18:00:00"), WAIVED, "away"))
        shift.add_break(Break(at("2026-10-14T13:00:00"), at("2026-10-14T14:00:00"), CLOCKED_OUT))
        self.assertEqual(shift.worked(shift.end), timedelta(hours=6))

    def test_a_break_left_after_the_shift_end_adds_no_time(self):
        shift = day_shift()
        shift.add_break(Break(at("2026-10-14T21:00:00"), at("2026-10-14T23:00:00"), WAIVED, "away"))
        self.assertEqual(shift.worked(shift.end), timedelta(hours=12))

    def test_the_last_return_is_the_latest_break_end_even_when_breaks_nest(self):
        shift = day_shift()
        shift.add_break(Break(at("2026-10-14T12:00:00"), at("2026-10-14T18:00:00"), WAIVED, "away"))
        shift.add_break(Break(at("2026-10-14T13:00:00"), at("2026-10-14T14:00:00"), CLOCKED_OUT))
        self.assertEqual(shift.since, at("2026-10-14T18:00:00"))

    def test_only_a_waived_break_is_found_as_a_waiver(self):
        shift = day_shift()
        shift.add_break(Break(at("2026-10-14T13:00:00"), at("2026-10-14T14:00:00"), CLOCKED_OUT))
        self.assertIsNone(shift.waived_from(at("2026-10-14T13:00:00")))


if __name__ == "__main__":
    unittest.main()
