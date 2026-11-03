import json
import os
import stat
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from chronata.adapters.storage.reminder_pace_file import MOST_BYTES, ReminderPaceFile
from chronata.use_cases.reminders.reminder_pace import ReminderPace

SETTINGS = Path("/settings/reminders.json")
OWNER = 1000
SAFE_OPENING = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


def fake_os(content: bytes = b"", mode: int = stat.S_IFREG | 0o600, owner: int = OWNER, size: int | None = None, cannot_open: bool = False) -> MagicMock:
    fake = MagicMock()
    fake.O_RDONLY, fake.O_NOFOLLOW, fake.O_NONBLOCK = os.O_RDONLY, os.O_NOFOLLOW, os.O_NONBLOCK
    fake.getuid.return_value = OWNER
    if cannot_open:
        fake.open.side_effect = OSError("refused")
    else:
        fake.open.return_value = 7
    measured = len(content)
    if size is not None:
        measured = size
    fake.fstat.return_value = MagicMock(st_mode=mode, st_uid=owner, st_size=measured)
    fake.read.return_value = content
    return fake


def loaded(fake: MagicMock) -> ReminderPace:
    with patch("chronata.adapters.storage.reminder_pace_file.os", fake):
        return ReminderPaceFile(SETTINGS).load()


def saved_as(minutes) -> bytes:
    return json.dumps({"clock_out_every_minutes": minutes}).encode("utf-8")


class ReadingTheReminderPace(unittest.TestCase):
    def test_it_opens_without_following_links_or_waiting_and_always_closes(self):
        fake = fake_os(saved_as(45))
        loaded(fake)
        fake.open.assert_called_once_with(SETTINGS, SAFE_OPENING)
        fake.close.assert_called_once_with(7)

    def test_a_saved_pace_is_read(self):
        self.assertEqual(loaded(fake_os(saved_as(45))), ReminderPace(timedelta(minutes=45)))

    def test_off_is_read(self):
        self.assertEqual(loaded(fake_os(saved_as(None))), ReminderPace(None))

    def test_a_file_that_cannot_be_opened_falls_back_to_every_half_hour(self):
        self.assertEqual(loaded(fake_os(cannot_open=True)), ReminderPace())

    def test_something_other_than_a_plain_file_falls_back_without_reading(self):
        for mode in (stat.S_IFDIR | 0o700, stat.S_IFIFO | 0o600):
            with self.subTest(mode=mode):
                fake = fake_os(saved_as(45), mode=mode)
                self.assertEqual(loaded(fake), ReminderPace())
                fake.read.assert_not_called()

    def test_a_file_owned_by_someone_else_falls_back_without_reading(self):
        fake = fake_os(saved_as(None), owner=OWNER + 1)
        self.assertEqual(loaded(fake), ReminderPace())
        fake.read.assert_not_called()

    def test_an_oversized_file_falls_back_without_reading(self):
        fake = fake_os(saved_as(None), size=MOST_BYTES + 1)
        self.assertEqual(loaded(fake), ReminderPace())
        fake.read.assert_not_called()

    def test_a_file_that_fails_while_reading_falls_back(self):
        fake = fake_os(saved_as(None))
        fake.read.side_effect = OSError("gone")
        self.assertEqual(loaded(fake), ReminderPace())
        fake.close.assert_called_once_with(7)

    def test_damaged_content_falls_back_to_every_half_hour(self):
        for content in (b"{not json", b"\xff\xfe", b"[" * 2048 + b"]" * 2048, b"[30]", b'"clock_out_every_minutes"'):
            with self.subTest(content=content[:12]):
                self.assertEqual(loaded(fake_os(content)), ReminderPace())

    def test_a_hand_edited_pace_outside_the_allowed_range_falls_back_to_every_half_hour(self):
        for minutes in (1, 0, 241, "30", True, 2.5):
            with self.subTest(minutes=minutes):
                self.assertEqual(loaded(fake_os(saved_as(minutes))), ReminderPace())


class SavingTheReminderPace(unittest.TestCase):
    def saved(self, pace: ReminderPace) -> dict:
        with patch("chronata.adapters.storage.reminder_pace_file.write_owner_only") as write:
            ReminderPaceFile(SETTINGS).save(pace)
        write.assert_called_once()
        path, content = write.call_args.args
        self.assertEqual(path, SETTINGS)
        return json.loads(content)

    def test_a_pace_is_saved_in_minutes(self):
        self.assertEqual(self.saved(ReminderPace(timedelta(minutes=45))), {"clock_out_every_minutes": 45})

    def test_off_is_saved_as_no_minutes(self):
        self.assertEqual(self.saved(ReminderPace(None)), {"clock_out_every_minutes": None})


if __name__ == "__main__":
    unittest.main()
