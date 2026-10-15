import unittest
from datetime import timedelta

from chronata.timekeeping.shifts.day_entries import day_entries
from chronata.timekeeping.shifts.shifts import Break, Shift
from tests.fakes import at


def shift(seq: int, start: str, end: str | None, label: str = "Northwind") -> Shift:
    return Shift(seq, at(start), at(end) if end else None, timedelta(), label)


class OneEntryPerDayAndLabel(unittest.TestCase):
    def test_the_pc_on_stretch_and_the_clocked_shift_are_one_day(self):
        after_lunch = shift(66, "2026-10-15T09:04:59", None)
        after_lunch.breaks.append(Break(at("2026-10-15T12:01:32"), at("2026-10-15T13:06:05"), "clocked out"))
        entries = day_entries([after_lunch, shift(67, "2026-10-15T08:41:52", "2026-10-15T09:04:59")])
        self.assertEqual(len(entries), 1)
        today = entries[0]
        self.assertEqual((today.start, today.end, [p.id for p in today.pieces]), (at("2026-10-15T08:41:52"), None, [67, 66]))
        self.assertEqual(today.worked(at("2026-10-15T14:00:00")), timedelta(hours=4, minutes=13, seconds=35))

    def test_another_label_the_same_day_is_its_own_entry(self):
        entries = day_entries([shift(1, "2026-10-15T08:00:00", "2026-10-15T12:00:00"), shift(2, "2026-10-15T18:00:00", "2026-10-15T20:00:00", "Acme")])
        self.assertEqual([(e.label, e.worked(at("2026-10-15T21:00:00"))) for e in entries], [("Northwind", timedelta(hours=4)), ("Acme", timedelta(hours=2))])

    def test_a_struck_out_piece_stays_in_the_entry_but_is_not_counted(self):
        struck = shift(2, "2026-10-15T13:00:00", "2026-10-15T14:00:00")
        struck.voided = True
        today = day_entries([shift(1, "2026-10-15T08:00:00", "2026-10-15T12:00:00"), struck])[0]
        self.assertEqual((len(today.pieces), today.worked(at("2026-10-15T15:00:00")), today.end), (2, timedelta(hours=4), at("2026-10-15T12:00:00")))


if __name__ == "__main__":
    unittest.main()
