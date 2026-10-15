import unittest
from datetime import date

from chronata.timekeeping.entries.clocking import ClockIn, ClockOut, ClockResumed
from chronata.timekeeping.entries.compensation import Compensated
from chronata.timekeeping.entries.corrections import BreakExplained, ShiftAdded, ShiftCorrected, ShiftVoided
from chronata.timekeeping.entries.labels import ShiftLabelled
from chronata.timekeeping.entries.pc import PcOffBreak, PowerSession
from tests.fakes import at

NINE = at("2026-10-15T09:00:00")
TEN = at("2026-10-15T10:00:00")


class WhatEachEntryRecords(unittest.TestCase):
    def test_the_sealed_format_stays_as_it_was(self):
        recorded = {
            ClockIn(NINE, "boot", "Northwind", "late bus"): ("clock_in", {"at": NINE.isoformat(), "boot": "boot", "label": "Northwind", "note": "late bus"}),
            ClockIn(NINE, "boot"): ("clock_in", {"at": NINE.isoformat(), "boot": "boot"}),
            ClockResumed(66, TEN, "boot"): ("clock_resumed", {"shift": 66, "at": TEN.isoformat(), "boot": "boot"}),
            ClockOut(66, TEN, "boot", " lunch "): ("clock_out", {"shift": 66, "at": TEN.isoformat(), "boot": "boot", "note": "lunch"}),
            ShiftAdded(NINE, TEN, "forgot", "Acme"): ("shift_added", {"start": NINE.isoformat(), "end": TEN.isoformat(), "reason": "forgot", "label": "Acme"}),
            ShiftCorrected(66, NINE, TEN, "typo"): ("shift_corrected", {"shift": 66, "start": NINE.isoformat(), "end": TEN.isoformat(), "reason": "typo"}),
            ShiftVoided(66, "mistake"): ("shift_voided", {"shift": 66, "reason": "mistake"}),
            BreakExplained(66, NINE.isoformat(), "power cut"): ("break_explained", {"shift": 66, "start": NINE.isoformat(), "reason": "power cut"}),
            ShiftLabelled(66, "Acme"): ("shift_labelled", {"shift": 66, "label": "Acme"}),
            ShiftLabelled(66, "Acme Ltd", "label renamed from Acme"): ("shift_labelled", {"shift": 66, "label": "Acme Ltd", "reason": "label renamed from Acme"}),
            PowerSession("boot", NINE, None): ("pc_session", {"boot": "boot", "on": NINE.isoformat(), "off": None}),
            PowerSession("boot", NINE, TEN, True): ("pc_session", {"boot": "boot", "on": NINE.isoformat(), "off": TEN.isoformat(), "exact": True}),
            PcOffBreak(66, NINE, TEN): ("pc_off_break", {"shift": 66, "start": NINE.isoformat(), "end": TEN.isoformat()}),
            Compensated(date(2026, 10, 1), date(2026, 10, 31), 2, False, "payslip", "Acme"):
                ("compensation", {"from": "2026-10-01", "to": "2026-10-31", "hours": 2, "label": "Acme", "kind": "paid", "reference": "payslip"}),
        }
        for entry, (kind, data) in recorded.items():
            self.assertEqual((entry.kind, entry.data()), (kind, data), entry)


if __name__ == "__main__":
    unittest.main()
