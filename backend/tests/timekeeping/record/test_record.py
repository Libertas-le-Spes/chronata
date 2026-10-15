import unittest

from chronata.timekeeping.record.record import GENESIS, chain_problems, sealed
from tests.fakes import at


def chain(count: int) -> list[dict]:
    records, previous = [], GENESIS
    for seq in range(1, count + 1):
        record = sealed(seq, "clock_in", {"at": f"2026-10-05T0{seq}:00:00+02:00"}, at("2026-10-05T09:00:00"), previous)
        records.append(record)
        previous = record["hash"]
    return records


class SealedChain(unittest.TestCase):
    def test_an_untouched_chain_has_no_problems(self):
        self.assertEqual(chain_problems(chain(3)), [])

    def test_an_edited_entry_is_caught(self):
        records = chain(3)
        records[0]["data"]["at"] = "2026-10-05T06:00:00+02:00"
        self.assertIn("line 1: contents were changed after it was written", chain_problems(records))

    def test_a_removed_entry_is_caught(self):
        records = chain(3)
        del records[1]
        self.assertTrue(chain_problems(records))


if __name__ == "__main__":
    unittest.main()
