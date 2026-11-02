import unittest
from datetime import timedelta

from chronata.use_cases.questions.questions import Answers, OffDefaultLabel
from tests.fakes import Fixture, at, hours


class SameDayShifts(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:03:00")
        self.f.app.setup.configure(hours("08:00", "17:00", "12:00", "60"))
        for label in ("Secondary", "Tertiary"):
            self.f.app.labels.create(label, Answers(no_set_hours=True))
        self.f.app.clocking.clock_in(None, None, "Secondary")

    def test_clocking_back_in_the_same_day_continues_the_shift_without_counting_the_break(self):
        self.f.at("2026-10-14T10:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T10:04:00")
        self.f.app.clocking.clock_in(None, None)
        self.f.at("2026-10-14T17:03:00")
        self.f.app.clocking.clock_out(None, None)
        self.assertEqual(len(self.f.app.log.shifts()), 1)
        self.assertEqual(self.f.app.log.weeks()[0].days[0].worked, timedelta(hours=8, minutes=56))

    def test_clocking_back_in_on_another_label_starts_a_new_shift(self):
        self.f.at("2026-10-14T10:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T10:04:00")
        self.f.app.clocking.clock_in(None, None, "Tertiary")
        self.assertEqual([(s.label, s.end) for s in self.f.app.log.shifts()], [("Secondary", at("2026-10-14T10:00:00")), ("Tertiary", None)])

    def test_clocking_back_in_on_the_same_label_continues_the_shift(self):
        self.f.at("2026-10-14T10:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T10:04:00")
        self.f.app.clocking.clock_in(None, None, "secondary")
        self.assertEqual(len(self.f.app.log.shifts()), 1)


class ClockingInOnTheDefault(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00", "12:00", "60"), "Primary")
        self.f.app.labels.create("Secondary", Answers(no_set_hours=True))

    def test_on_a_workday_another_label_asks_first_and_records_nothing(self):
        with self.assertRaises(OffDefaultLabel) as raised:
            self.f.app.clocking.clock_in(None, None, "Secondary")
        self.assertEqual((raised.exception.label, raised.exception.default_label), ("Secondary", "Primary"))
        self.assertEqual(self.f.app.log.shifts(), [])

    def test_confirming_clocks_in_on_the_other_label(self):
        self.f.app.clocking.clock_in(None, None, "Secondary", Answers(off_default=True))
        self.assertEqual(self.f.app.log.shifts()[0].label, "Secondary")

    def test_no_label_on_a_workday_asks_too(self):
        with self.assertRaises(OffDefaultLabel):
            self.f.app.clocking.clock_in(None, None, "")

    def test_the_default_goes_straight_in_whatever_the_capitals(self):
        self.f.app.clocking.clock_in(None, None, " primary")
        self.assertEqual(self.f.app.log.shifts()[0].label, "Primary")

    def test_clocking_in_without_choosing_uses_the_default(self):
        self.f.app.clocking.clock_in(None, None)
        self.assertEqual(self.f.app.log.shifts()[0].label, "Primary")

    def test_at_the_weekend_another_label_does_not_ask(self):
        self.f.at("2026-10-17T10:00:00")
        self.f.app.clocking.clock_in(None, None, "Secondary")
        self.assertEqual(self.f.app.log.shifts()[0].label, "Secondary")

    def test_without_a_default_nothing_asks(self):
        self.f.app.labels.set_default("")
        self.f.app.clocking.clock_in(None, None, "Secondary")
        self.assertEqual(self.f.app.log.shifts()[0].label, "Secondary")



class LunchAfterALateStart(unittest.TestCase):
    def test_clocking_out_ten_minutes_later_for_lunch_makes_up_ten_minutes_late(self):
        f = Fixture("2026-10-14T08:40:00")
        f.app.setup.configure(hours("08:30", "17:30", "12:00", "60"))
        f.app.clocking.clock_in(None, None)
        f.at("2026-10-14T12:10:00")
        f.app.clocking.clock_out(None, None)
        f.at("2026-10-14T12:30:00")
        today = f.app.log.weeks()[0].days[0]
        self.assertEqual((today.punctuality.late, today.punctuality.made_up), (timedelta(minutes=10), True))


if __name__ == "__main__":
    unittest.main()
