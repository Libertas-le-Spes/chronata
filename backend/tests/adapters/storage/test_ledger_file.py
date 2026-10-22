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

    def test_a_line_cut_short_by_a_power_cut_is_reported_and_nothing_is_added_after_it(self):
        with self.ledger.path.open("a") as file:
            file.write('{"seq": 3, "kind": "clock_o')
        self.assertEqual(len(self.ledger.entries()), 2)
        self.assertIn("line 3: is not a whole entry", self.ledger.problems()[0])
        with self.assertRaises(TamperedRecord):
            self.ledger.append("clock_in", {"at": "2026-10-06T08:00:00+02:00"}, at("2026-10-06T08:00:00"))

    def test_lines_that_are_not_entries_are_reported_not_crashed_on(self):
        with self.ledger.path.open("ab") as file:
            file.write(b'[1, 2]\n"text"\n{"seq": 3}\n\xff\xfe\n')
        self.assertEqual((len(self.ledger.entries()), len([p for p in self.ledger.problems() if "not a whole entry" in p])), (2, 4))

    def test_the_ledger_is_kept_where_only_its_owner_can_open_it(self):
        self.assertEqual(self.ledger.path.stat().st_mode & 0o077, 0)


if __name__ == "__main__":
    unittest.main()
