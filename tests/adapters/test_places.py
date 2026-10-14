import base64
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from chronata.adapters.git.history import GitHistory
from chronata.adapters.places.place_book import PlaceBook
from chronata.adapters.places.webdav_upload import upload_changed
from chronata.use_cases.ports import SaveError


class Folders(unittest.TestCase):
    def setUp(self):
        self.book = PlaceBook(Path(tempfile.mkdtemp()), GitHistory(Path(tempfile.mkdtemp()), "ledger.jsonl"))

    def test_a_folder_that_is_not_a_vault_is_refused_as_one(self):
        with self.assertRaises(SaveError):
            self.book.add("obsidian", "", tempfile.mkdtemp())

    def test_a_vault_gets_its_own_chronata_folder(self):
        vault = Path(tempfile.mkdtemp())
        (vault / ".obsidian").mkdir()
        self.book.deliver(self.book.add("obsidian", "", str(vault)), {"Days/2026-10-13.md": b"note"})
        self.assertEqual((vault / "Chronata" / "Days" / "2026-10-13.md").read_bytes(), b"note")

    def test_unchanged_files_are_left_alone(self):
        folder = Path(tempfile.mkdtemp())
        place = self.book.add("folder", "", str(folder))
        self.book.deliver(place, {"a.txt": b"same"})
        before = (folder / "a.txt").stat().st_mtime_ns
        self.book.deliver(place, {"a.txt": b"same"})
        self.assertEqual((folder / "a.txt").stat().st_mtime_ns, before)

    def test_the_place_list_is_private_to_this_user(self):
        self.book.add("folder", "", tempfile.mkdtemp())
        self.assertEqual(self.book.path.stat().st_mode & 0o077, 0)


class FakeWebDav(BaseHTTPRequestHandler):
    files: dict[str, bytes] = {}
    folders: set[str] = set()
    puts: list[str] = []

    def authorised(self) -> bool:
        if self.headers.get("Authorization") != "Basic " + base64.b64encode(b"kabelo:secret").decode():
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
        self.address = f"http://127.0.0.1:{self.server.server_port}/dav"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_files_are_uploaded_into_folders_and_only_changes_are_sent_again(self):
        bundle = {"sealed/ledger.jsonl": b"one", "Days/2026-10-13.md": b"note"}
        sent = upload_changed(self.address, "kabelo", "secret", bundle, {})
        self.assertEqual(FakeWebDav.files["/dav/Chronata/sealed/ledger.jsonl"], b"one")
        upload_changed(self.address, "kabelo", "secret", {**bundle, "sealed/ledger.jsonl": b"two"}, sent)
        self.assertEqual(FakeWebDav.puts.count("/dav/Chronata/Days/2026-10-13.md"), 1)
        self.assertEqual(FakeWebDav.files["/dav/Chronata/sealed/ledger.jsonl"], b"two")

    def test_a_wrong_password_says_so(self):
        with self.assertRaisesRegex(SaveError, "refused the username or password"):
            upload_changed(self.address, "kabelo", "wrong", {"a.txt": b"x"}, {})


if __name__ == "__main__":
    unittest.main()
