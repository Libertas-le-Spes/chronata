import unittest
from datetime import timedelta

from chronata.adapters.power_history.last_log import boots_from_last
from chronata.adapters.power_history.windows_events import boots_from_events, events_from_xml
from tests.fakes import at

LAST_OUTPUT = """\
reboot   system boot  7.2.5-3-omarchy  2026-10-15T08:45:06+02:00   still running
reboot   system boot  7.2.5-3-omarchy  2026-10-14T08:33:10+02:00 - 2026-10-14T18:31:27+02:00  (09:58)
reboot   system boot  7.2.5-3-omarchy  2026-10-12T08:36:21+02:00 - crash                      (02:57)
"""

EVENT = ('<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event"><System>'
         '<EventID>{id}</EventID><TimeCreated SystemTime="{time}"/></System></Event>')


def events(*pairs: tuple[str, str]) -> str:
    return "".join(EVENT.format(id=event_id, time=time) for event_id, time in pairs)


class LinuxWithoutSystemd(unittest.TestCase):
    def test_reboot_lines_give_each_session_its_start_and_end(self):
        self.assertEqual(boots_from_last(LAST_OUTPUT), [
            (at("2026-10-15T08:45:06"), None),
            (at("2026-10-14T08:33:10"), at("2026-10-14T18:31:27")),
            (at("2026-10-12T08:36:21"), at("2026-10-12T08:36:21") + timedelta(hours=2, minutes=57)),
        ])


class Windows(unittest.TestCase):
    def test_a_clean_shutdown_is_exact_and_the_running_session_is_current(self):
        found = events_from_xml(events(("6005", "2026-10-14T06:33:10.1234567Z"), ("6006", "2026-10-14T16:31:27.5Z"),
                                       ("6005", "2026-10-15T06:45:06.0Z")))
        boots = boots_from_events(found, at("2026-10-15T08:45:06"), at("2026-10-15T09:00:00"))
        self.assertEqual([(b.on, b.last_seen, b.current, b.off_is_exact) for b in boots], [
            (at("2026-10-14T08:33:10"), at("2026-10-14T18:31:27"), False, True),
            (at("2026-10-15T08:45:06"), at("2026-10-15T09:00:00"), True, False),
        ])

    def test_a_start_with_no_clean_stop_is_kept_without_inventing_an_end(self):
        found = events_from_xml(events(("6005", "2026-10-14T06:33:10Z"), ("6005", "2026-10-15T06:45:06Z")))
        first = boots_from_events(found, at("2026-10-15T08:45:06"), at("2026-10-15T09:00:00"))[0]
        self.assertEqual((first.on, first.last_seen, first.off_is_exact), (at("2026-10-14T08:33:10"), at("2026-10-14T08:33:10"), False))


if __name__ == "__main__":
    unittest.main()
