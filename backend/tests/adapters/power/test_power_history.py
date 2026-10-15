import unittest
from datetime import timedelta

from chronata.adapters.power.last_log import boots_from_last
from tests.fakes import at

LAST_OUTPUT = """\
reboot   system boot  7.2.5-3-omarchy  2026-10-15T08:45:06+02:00   still running
reboot   system boot  7.2.5-3-omarchy  2026-10-14T08:33:10+02:00 - 2026-10-14T18:31:27+02:00  (09:58)
reboot   system boot  7.2.5-3-omarchy  2026-10-12T08:36:21+02:00 - crash                      (02:57)
"""

class LinuxWithoutSystemd(unittest.TestCase):
    def test_reboot_lines_give_each_session_its_start_and_end(self):
        self.assertEqual(boots_from_last(LAST_OUTPUT), [
            (at("2026-10-15T08:45:06"), None),
            (at("2026-10-14T08:33:10"), at("2026-10-14T18:31:27")),
            (at("2026-10-12T08:36:21"), at("2026-10-12T08:36:21") + timedelta(hours=2, minutes=57)),
        ])


if __name__ == "__main__":
    unittest.main()
