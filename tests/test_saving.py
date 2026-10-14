import base64
import json
import shutil
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from chronata import places, timestamps, verification
from chronata.audit_trail import AuditTrail
from chronata.ledger import Ledger

FIXTURES = Path(__file__).parent / "fixtures"
RECEIPT_HASH = (FIXTURES / "digicert.hash").read_text().strip()


def receipt_in(folder: Path, seq: int = 1) -> timestamps.Stamp:
    (folder / timestamps.FOLDER).mkdir(parents=True, exist_ok=True)
    path = folder / timestamps.FOLDER / f"{seq:06d}-{RECEIPT_HASH[:12]}-digicert.tsr"
    shutil.copy(FIXTURES / "digicert.tsr", path)
    return timestamps.stamps(folder)[0]


class Receipts(unittest.TestCase):
    def test_a_real_receipt_is_read_and_its_signature_checks_out(self):
        stamp = receipt_in(Path(tempfile.mkdtemp()))
        self.assertEqual(stamp.authority, "digicert")
        self.assertEqual(stamp.time.tzinfo, timezone.utc)
        self.assertIsNone(timestamps.check(stamp, RECEIPT_HASH))

    def test_a_receipt_does_not_vouch_for_a_different_entry(self):
        stamp = receipt_in(Path(tempfile.mkdtemp()))
        self.assertIn("different entry", timestamps.check(stamp, "00" * 32))

    def test_a_damaged_receipt_is_caught(self):
        stamp = receipt_in(Path(tempfile.mkdtemp()))
        damaged = bytearray(stamp.path.read_bytes())
        damaged[-40] ^= 0xFF
        stamp.path.write_bytes(bytes(damaged))
        self.assertIsNotNone(timestamps.check(stamp, RECEIPT_HASH))


class CheckingACopy(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        ledger = Ledger(self.folder / "ledger.jsonl")
        ledger.append("clock_in", {"at": "2026-10-13T08:00:00+02:00"}, datetime(2026, 10, 13, 8, tzinfo=timezone.utc))
        self.ledger = ledger

    def test_a_receipt_for_an_entry_that_is_not_there_is_reported(self):
        receipt_in(self.folder, seq=5)
        problems = verification.check(self.ledger, self.folder).problems
        self.assertTrue(any("missing from the log" in p for p in problems))

    def test_the_sealed_folder_is_found_whichever_folder_is_given(self):
        vault = Path(tempfile.mkdtemp())
        sealed = vault / "Chronata" / "sealed"
        sealed.mkdir(parents=True)
        shutil.copy(self.ledger.path, sealed / "ledger.jsonl")
        self.assertEqual(verification.sealed_folder(vault), sealed)
        with self.assertRaises(FileNotFoundError):
            verification.sealed_folder(Path(tempfile.mkdtemp()))


class Folders(unittest.TestCase):
    def setUp(self):
        self.config = Path(tempfile.mkdtemp())
        repo = Path(tempfile.mkdtemp())
        self.trail = AuditTrail(repo)
        self.trail.ensure()
        self.book = places.PlaceBook(self.config, self.trail)

    def test_a_folder_that_is_not_a_vault_is_refused_as_one(self):
        with self.assertRaises(places.SaveError):
            self.book.add("obsidian", "", tempfile.mkdtemp())

    def test_a_vault_gets_its_own_chronata_folder(self):
        vault = Path(tempfile.mkdtemp())
        (vault / ".obsidian").mkdir()
        place = self.book.add("obsidian", "", str(vault))
        places.save(place, {"Days/2026-10-13.md": b"note"}, self.trail, {})
        self.assertEqual((vault / "Chronata" / "Days" / "2026-10-13.md").read_bytes(), b"note")

    def test_unchanged_files_are_left_alone(self):
        folder = Path(tempfile.mkdtemp())
        place = self.book.add("folder", "", str(folder))
        places.save(place, {"a.txt": b"same"}, self.trail, {})
        before = (folder / "a.txt").stat().st_mtime_ns
        places.save(place, {"a.txt": b"same"}, self.trail, {})
        self.assertEqual((folder / "a.txt").stat().st_mtime_ns, before)

    def test_the_place_list_is_private_to_this_user(self):
        self.book.add("folder", "", tempfile.mkdtemp())
        self.assertEqual(self.book.path.stat().st_mode & 0o077, 0)


class FakeWebDav(BaseHTTPRequestHandler):
    files: dict[str, bytes] = {}
    folders: set[str] = set()
    puts: list[str] = []

    def authorised(self) -> bool:
        expected = "Basic " + base64.b64encode(b"kabelo:secret").decode()
        if self.headers.get("Authorization") != expected:
            self.send_response(401)
            self.end_headers()
            return False
        return True

    def do_MKCOL(self):
        if self.authorised():
            self.send_response(405 if self.path in self.folders else 201)
            self.folders.add(self.path)
            self.end_headers()

    def do_PUT(self):
        if self.authorised():
            self.files[self.path] = self.rfile.read(int(self.headers["Content-Length"]))
            self.puts.append(self.path)
            self.send_response(201)
            self.end_headers()

    def log_message(self, *args):
        pass


class WebServers(unittest.TestCase):
    def setUp(self):
        FakeWebDav.files, FakeWebDav.folders, FakeWebDav.puts = {}, set(), []
        self.server = HTTPServer(("127.0.0.1", 0), FakeWebDav)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/dav"
        self.trail = AuditTrail(Path(tempfile.mkdtemp()))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def place(self, password: str) -> places.Place:
        return places.Place("webdav-1", "webdav", "Server", self.url, "kabelo", password)

    def test_files_are_uploaded_into_folders_and_only_changes_are_sent_again(self):
        bundle = {"sealed/ledger.jsonl": b"one", "Days/2026-10-13.md": b"note"}
        sent = places.save(self.place("secret"), bundle, self.trail, {})
        self.assertEqual(FakeWebDav.files["/dav/Chronata/sealed/ledger.jsonl"], b"one")
        places.save(self.place("secret"), {**bundle, "sealed/ledger.jsonl": b"two"}, self.trail, sent)
        self.assertEqual(FakeWebDav.puts.count("/dav/Chronata/Days/2026-10-13.md"), 1)
        self.assertEqual(FakeWebDav.files["/dav/Chronata/sealed/ledger.jsonl"], b"two")

    def test_a_wrong_password_says_so(self):
        with self.assertRaisesRegex(places.SaveError, "refused the username or password"):
            places.save(self.place("wrong"), {"a.txt": b"x"}, self.trail, {})


if __name__ == "__main__":
    unittest.main()
