import shutil
import tempfile
import unittest
from datetime import timezone
from pathlib import Path

from chronata.adapters.timestamping.rfc3161 import Rfc3161Timestamper

FIXTURES = Path(__file__).parent / "fixtures"
RECEIPT_HASH = (FIXTURES / "digicert.hash").read_text().strip()


def timestamper_holding_receipt(seq: int = 1) -> Rfc3161Timestamper:
    folder = Path(tempfile.mkdtemp())
    shutil.copy(FIXTURES / "digicert.tsr", folder / f"{seq:06d}-{RECEIPT_HASH[:12]}-digicert.tsr")
    return Rfc3161Timestamper(folder)


class Receipts(unittest.TestCase):
    def test_a_real_receipt_is_read_and_its_signature_checks_out(self):
        timestamper = timestamper_holding_receipt()
        stamp = timestamper.stamps()[0]
        self.assertEqual((stamp.authority_name, stamp.time.tzinfo), ("DigiCert", timezone.utc))
        self.assertIsNone(timestamper.check(stamp, RECEIPT_HASH))

    def test_a_receipt_does_not_vouch_for_a_different_entry(self):
        timestamper = timestamper_holding_receipt()
        self.assertIn("different entry", timestamper.check(timestamper.stamps()[0], "00" * 32))

    def test_a_damaged_receipt_is_caught(self):
        timestamper = timestamper_holding_receipt()
        stamp = timestamper.stamps()[0]
        path = timestamper.folder / stamp.name
        damaged = bytearray(path.read_bytes())
        damaged[-40] ^= 0xFF
        path.write_bytes(bytes(damaged))
        self.assertIsNotNone(timestamper.check(stamp, RECEIPT_HASH))


if __name__ == "__main__":
    unittest.main()
