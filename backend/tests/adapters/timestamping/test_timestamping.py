import os
import tempfile
import threading
import unittest
from datetime import timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from chronata.adapters.timestamping.rfc3161 import LARGEST_REPLY, Rfc3161Timestamper, _ask
from chronata.adapters.timestamping.receipt_check import ReceiptRefused
from chronata.use_cases.log.ports import CannotCheck

FIXTURES = Path(__file__).parent / "fixtures"
RECEIPT_HASH = (FIXTURES / "digicert.hash").read_text().strip()
RECEIPT = (FIXTURES / "digicert.tsr").read_bytes()
OTHER_HASH = "ab" * 32


def holding(name: str, hash_of=lambda seq: RECEIPT_HASH if seq == 1 else None, checked: Path | None = None) -> Rfc3161Timestamper:
    folder = Path(tempfile.mkdtemp())
    (folder / name).write_bytes(RECEIPT)
    return Rfc3161Timestamper(folder, hash_of, checked)


GENUINE = f"000001-{RECEIPT_HASH[:12]}-digicert.tsr"


class AGenuineReceipt(unittest.TestCase):
    def test_is_shown_with_its_signed_time(self):
        stamp = holding(GENUINE).stamps()[0]
        self.assertEqual((stamp.authority_name, stamp.time.tzinfo), ("DigiCert", timezone.utc))
        self.assertEqual(holding(GENUINE).problems(), [])

    def test_once_checked_is_not_checked_again_until_it_changes(self):
        checked = Path(tempfile.mkdtemp()) / "checked.json"
        timestamper = holding(GENUINE, checked=checked)
        first = timestamper.stamps()
        with mock.patch("shutil.which", return_value=None):
            self.assertEqual(timestamper.stamps(), first)
            (timestamper.folder / GENUINE).write_bytes(RECEIPT[:-1] + bytes([RECEIPT[-1] ^ 1]))
            self.assertEqual(timestamper.stamps(), [])


class AReceiptThatDoesNotVouch(unittest.TestCase):
    def test_for_a_rolled_back_entry_is_not_shown_and_is_reported(self):
        timestamper = holding(GENUINE, hash_of=lambda seq: OTHER_HASH)
        self.assertEqual(timestamper.stamps(), [])
        self.assertIn("different version of entry 1", timestamper.problems()[0])

    def test_damaged_is_reported(self):
        timestamper = holding(GENUINE)
        (timestamper.folder / GENUINE).write_bytes(RECEIPT[:-40] + bytes([RECEIPT[-40] ^ 0xFF]) + RECEIPT[-39:])
        self.assertEqual(timestamper.stamps(), [])
        self.assertIn("not a genuine DigiCert receipt", timestamper.problems()[0])

    def test_claiming_another_authority_is_refused_by_that_authoritys_own_root(self):
        timestamper = holding(f"000001-{RECEIPT_HASH[:12]}-freetsa.tsr")
        self.assertEqual(timestamper.stamps(), [])
        self.assertIn("not a genuine FreeTSA receipt", timestamper.problems()[0])

    def test_from_an_unknown_authority_or_with_a_stray_name_does_not_crash_anything(self):
        timestamper = holding(f"000001-{RECEIPT_HASH[:12]}-madeup.tsr")
        (timestamper.folder / "notes.tsr").write_bytes(b"\x30" * 30000)
        self.assertEqual(timestamper.stamps(), [])
        self.assertEqual(len(timestamper.problems()), 1)


class WithoutOpenssl(unittest.TestCase):
    def test_nothing_is_vouched_for(self):
        timestamper = holding(GENUINE)
        with mock.patch("shutil.which", return_value=None):
            self.assertEqual(timestamper.stamps(), [])
            with self.assertRaises(CannotCheck):
                timestamper.problems()


class AReplyFromTheNetwork(unittest.TestCase):
    def test_that_answers_a_different_request_is_not_kept(self):
        timestamper = Rfc3161Timestamper(Path(tempfile.mkdtemp()), lambda seq: RECEIPT_HASH, ask=lambda url, query: RECEIPT)
        made, failures = timestamper.stamp(1, RECEIPT_HASH)
        self.assertEqual((made, list(timestamper.folder.iterdir())), ([], []))
        self.assertEqual(len(failures), 2)

    def test_far_larger_than_a_receipt_is_refused(self):
        class Huge(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"x" * (LARGEST_REPLY * 2))

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Huge)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with mock.patch.dict(os.environ, {"no_proxy": "127.0.0.1"}), self.assertRaises(ReceiptRefused):
                _ask(f"http://127.0.0.1:{server.server_port}/", b"query")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
