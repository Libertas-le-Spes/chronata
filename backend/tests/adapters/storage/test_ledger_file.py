import json
import tempfile
import unittest
from pathlib import Path

from chronata.adapters.storage.ledger_file import LedgerFile
from chronata.timekeeping.record.record import TamperedRecord
from tests.fakes import at


class LedgerOnDisk(unittest.TestCase):
    def setUp(self):
        self.ledger = LedgerFile(Path(tempfile.mkdtemp()) / "ledger.jsonl")
        for hour in (8, 17):
            self.ledger.append("clock_in", {"at": f"2026-10-05T{hour:02d}:00:00+02:00"}, at("2026-10-05T18:00:00"))

    def test_nothing_can_be_added_after_the_file_was_edited_by_hand(self):
        lines = self.ledger.path.read_text().splitlines()
        record = json.loads(lines[0])
        record["data"]["at"] = "2026-10-05T06:00:00+02:00"
        self.ledger.path.write_text("\n".join([json.dumps(record), *lines[1:]]) + "\n")
        self.assertTrue(self.ledger.problems())
        with self.assertRaises(TamperedRecord):
            self.ledger.append("clock_in", {"at": "2026-10-06T08:00:00+02:00"}, at("2026-10-06T08:00:00"))

    def test_head_and_hashes_point_at_saved_entries(self):
        self.assertEqual(self.ledger.head()[0], 2)
        self.assertIsNone(self.ledger.hash_of(3))


if __name__ == "__main__":
    unittest.main()
