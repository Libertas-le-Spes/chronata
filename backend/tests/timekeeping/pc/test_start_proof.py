import unittest
from datetime import timedelta, timezone

from chronata.presenters.text.explanation import started
from chronata.timekeeping.pc.pc_sessions import PcSession
from chronata.timekeeping.pc.start_proof import start_proof
from chronata.timekeeping.record.stamps import Stamp
from chronata.timekeeping.shifts.shifts import Shift
from tests.fakes import at

SESSIONS = [PcSession("today", at("2026-10-15T08:41:52"), None, False, 65)]


def stamp(seq: int, authority: str, when: str) -> Stamp:
    return Stamp(seq, authority.lower(), authority, at(when).astimezone(timezone.utc), f"{seq}-{authority}")


STAMPS = [stamp(65, "DigiCert", "2026-10-15T08:45:18"), stamp(65, "FreeTSA", "2026-10-15T08:45:19"),
          stamp(66, "DigiCert", "2026-10-15T09:08:15"), stamp(67, "DigiCert", "2026-10-15T09:40:38")]


class WhatProvesTheStart(unittest.TestCase):
    def test_a_shift_from_when_the_pc_came_on_is_proven_by_the_pc_record_stamps(self):
        shift = Shift(67, at("2026-10-15T08:41:52"), at("2026-10-15T09:04:59"), timedelta(minutes=32), "Northwind")
        proof = start_proof(shift, SESSIONS, STAMPS)
        self.assertEqual((proof.from_pc_on, proof.entry), (True, 65))
        self.assertEqual(started(proof, shift.start), "started when the PC came on at 08:41:52 · independently timestamped by DigiCert 08:45:18, FreeTSA 08:45:19")

    def test_a_corrected_start_still_shows_it_began_when_the_pc_came_on(self):
        shift = Shift(67, at("2026-10-15T08:41:52"), at("2026-10-15T09:04:59"), timedelta(minutes=32), "Northwind")
        shift.start = at("2026-10-15T08:30:00")
        self.assertEqual(start_proof(shift, SESSIONS, STAMPS).from_pc_on, True)

    def test_a_clock_in_is_proven_by_the_first_stamps_covering_its_own_entry(self):
        shift = Shift(66, at("2026-10-15T09:04:59"), None, timedelta(), "Northwind")
        self.assertEqual(started(start_proof(shift, SESSIONS, STAMPS), shift.start), "start logged in entry 66 · independently timestamped by DigiCert 09:08:15")

    def test_a_shift_not_yet_stamped_says_so(self):
        shift = Shift(68, at("2026-10-15T10:00:00"), None, timedelta(), "Northwind")
        self.assertEqual(started(start_proof(shift, SESSIONS, STAMPS), shift.start), "start logged in entry 68 · not yet independently timestamped")


if __name__ == "__main__":
    unittest.main()
