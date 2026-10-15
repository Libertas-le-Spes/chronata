import unittest

from chronata.timekeeping.pc.pc_sessions import PcSession, support
from tests.fakes import at

SESSIONS = [PcSession("a", at("2026-10-13T08:30:00"), at("2026-10-13T12:00:00")), PcSession("b", at("2026-10-13T13:00:00"), None)]
EVENING = at("2026-10-13T20:00:00")


class PcSupport(unittest.TestCase):
    def test_a_shift_inside_a_session_is_fully_supported(self):
        self.assertEqual(support(at("2026-10-13T09:00:00"), at("2026-10-13T11:00:00"), SESSIONS, EVENING).share, 1.0)

    def test_a_restart_in_the_middle_of_a_shift_leaves_a_gap(self):
        backing = support(at("2026-10-13T11:00:00"), at("2026-10-13T14:00:00"), SESSIONS, EVENING)
        self.assertAlmostEqual(backing.share, 2 / 3)
        self.assertEqual([s.boot for s in backing.sessions], ["a", "b"])

    def test_a_shift_before_any_pc_record_says_so(self):
        backing = support(at("2026-10-01T09:00:00"), at("2026-10-01T17:00:00"), SESSIONS, EVENING)
        self.assertEqual((backing.before_records, backing.sessions), (True, ()))


if __name__ == "__main__":
    unittest.main()
