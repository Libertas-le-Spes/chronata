import json
import unittest
from unittest.mock import create_autospec

from chronata.adapters.storage.away_file import AwayFile
from chronata.adapters.storage.owner_only_folder import OwnerOnlyFolder
from chronata.use_cases.away.away_stretch import AwayStretch
from chronata.use_cases.log.ports import NotPrivate
from tests.fakes import at

LEFT = at("2026-10-14T18:00:00")
BACK = at("2026-10-14T19:40:00")


def folder_holding(text: str | None) -> OwnerOnlyFolder:
    folder = create_autospec(OwnerOnlyFolder, instance=True)
    folder.read.return_value = text
    return folder


class ReadingTheTimeAway(unittest.TestCase):
    def test_a_kept_time_away_is_read(self):
        text = json.dumps({"shift": 4, "since": LEFT.isoformat(), "back": BACK.isoformat()})
        self.assertEqual(AwayFile(folder_holding(text)).load(), AwayStretch(4, LEFT, BACK))

    def test_a_time_away_still_going_is_read(self):
        text = json.dumps({"shift": 4, "since": LEFT.isoformat(), "back": None})
        self.assertEqual(AwayFile(folder_holding(text)).load(), AwayStretch(4, LEFT))

    def test_nothing_kept_reads_as_nothing(self):
        self.assertIsNone(AwayFile(folder_holding(None)).load())

    def test_damaged_content_reads_as_nothing(self):
        for text in ("{not json", "[4]", "4", json.dumps({"shift": "4", "since": LEFT.isoformat(), "back": None}),
                     json.dumps({"shift": 4, "since": "yesterday", "back": None}), json.dumps({"shift": 4, "since": "2026-10-14T18:00:00", "back": None}),
                     json.dumps({"shift": 4, "since": 5, "back": None}), json.dumps({"shift": 4})):
            with self.subTest(text=text):
                self.assertIsNone(AwayFile(folder_holding(text)).load())

    def test_a_folder_that_is_not_private_or_cannot_be_read_reads_as_nothing(self):
        for failure in (NotPrivate("shared"), OSError("gone"), ValueError("not text")):
            with self.subTest(failure=failure):
                folder = folder_holding(None)
                folder.read.side_effect = failure
                self.assertIsNone(AwayFile(folder).load())


class KeepingTheTimeAway(unittest.TestCase):
    def test_it_is_written_to_the_private_folder(self):
        folder = folder_holding(None)
        AwayFile(folder).keep(AwayStretch(4, LEFT, BACK))
        folder.write.assert_called_once_with("away.json", json.dumps({"shift": 4, "since": LEFT.isoformat(), "back": BACK.isoformat()}))

    def test_forgetting_removes_it(self):
        folder = folder_holding(None)
        AwayFile(folder).forget()
        folder.forget.assert_called_once_with("away.json")


if __name__ == "__main__":
    unittest.main()
