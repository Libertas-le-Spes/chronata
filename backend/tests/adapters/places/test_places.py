import base64
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from chronata.adapters.places.kinds.folder_place import FolderPlace, ObsidianVault
from chronata.adapters.places.place_book import PlaceBook
from chronata.adapters.places.place_kind import SavedPlace
from chronata.adapters.places.transport.git_folder import GitFolders
from chronata.adapters.places.transport.git_push import GitRemotes
from chronata.adapters.places.transport.webdav_upload import upload_changed
from chronata.use_cases.log.ports import PlaceKindDescription, SaveError


class Folders(unittest.TestCase):
    def setUp(self):
        self.book = PlaceBook(Path(tempfile.mkdtemp()), [ObsidianVault(), FolderPlace()])

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


class GitPlaces(unittest.TestCase):
    def setUp(self):
        self.log = Path(tempfile.mkdtemp())
        subprocess.run(["git", "-C", str(self.log), "init", "-q", "-b", "main"], check=True)
        (self.log / "ledger.jsonl").write_text("entry\n")
        subprocess.run(["git", "-C", str(self.log), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.log), "commit", "-q", "-m", "entry"], check=True)
        self.remotes = GitRemotes(self.log)

    def test_the_log_is_pushed_to_a_git_place(self):
        backup = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(backup)], check=True)
        self.remotes.add("backup", str(backup))
        self.remotes.push("backup")
        pushed = subprocess.run(["git", "-C", str(backup), "log", "--format=%s"], capture_output=True, text=True).stdout
        self.assertEqual(pushed.strip(), "entry")

    def test_a_place_that_cannot_be_reached_says_so(self):
        self.remotes.add("nowhere", str(Path(tempfile.mkdtemp()) / "missing.git"))
        with self.assertRaisesRegex(SaveError, "will try again on the next save"):
            self.remotes.push("nowhere")


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


class FoldersInAGitRepository(unittest.TestCase):
    def setUp(self):
        self.remote = Path(tempfile.mkdtemp()) / "notes.git"
        git("init", "-q", "--bare", "-b", "main", str(self.remote), cwd=Path("/"))
        self.mine = Path(tempfile.mkdtemp())
        git("clone", "-q", str(self.remote), ".", cwd=self.mine)
        (self.mine / "Portfolio").mkdir()
        (self.mine / "Portfolio" / "note.md").write_text("my own note\n")
        git("add", "-A", cwd=self.mine)
        git("commit", "-q", "-m", "my notes", cwd=self.mine)
        git("push", "-q", "origin", "main", cwd=self.mine)
        self.folders = GitFolders(Path(tempfile.mkdtemp()))

    def test_only_the_chosen_folder_is_written_and_nothing_else_changes(self):
        self.folders.save("p1", str(self.remote), "Work Logs", {"README.md": b"logs", "Northwind/Days/2026-10-14.md": b"day"})
        changed = git("show", "--name-only", "--format=", "main", cwd=self.remote).splitlines()
        self.assertTrue(changed and all(path.startswith("Work Logs/") for path in changed))
        self.assertEqual(git("show", "main:Portfolio/note.md", cwd=self.remote), "my own note\n")

    def test_work_pushed_from_elsewhere_in_between_is_kept(self):
        self.folders.save("p1", str(self.remote), "Work Logs", {"README.md": b"first"})
        git("pull", "-q", "--rebase", cwd=self.mine)
        (self.mine / "Portfolio" / "later.md").write_text("written in Obsidian\n")
        git("add", "-A", cwd=self.mine)
        git("commit", "-q", "-m", "later", cwd=self.mine)
        git("push", "-q", "origin", "main", cwd=self.mine)
        self.folders.save("p1", str(self.remote), "Work Logs", {"README.md": b"second"})
        self.assertEqual(git("show", "main:Portfolio/later.md", cwd=self.remote), "written in Obsidian\n")
        self.assertEqual(git("show", "main:Work Logs/README.md", cwd=self.remote), "second")

    def test_a_folder_chronata_did_not_make_is_left_alone(self):
        with self.assertRaisesRegex(SaveError, "was not made by Chronata"):
            self.folders.prepare("p2", str(self.remote), "Portfolio")


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



class Notebook:
    id = "notebook"
    needs_local_history = False
    description = PlaceKindDescription("Notebook", "Page", "front", False, False, False, "Writes on paper.")

    def __init__(self):
        self.pages: dict[str, dict[str, bytes]] = {}

    def accept(self, place: SavedPlace) -> SavedPlace:
        return place

    def added(self, place: SavedPlace) -> None:
        self.pages[place.target] = {}

    def removed(self, place: SavedPlace) -> None:
        del self.pages[place.target]

    def deliver(self, place: SavedPlace, bundle: dict[str, bytes]) -> None:
        self.pages[place.target] = bundle

    def already_there(self) -> list[SavedPlace]:
        return []


class ANewKindOfPlace(unittest.TestCase):
    def test_needs_only_its_own_class(self):
        notebook = Notebook()
        book = PlaceBook(Path(tempfile.mkdtemp()), [notebook])
        place = book.add("notebook", "", "front")
        book.deliver(place, {"a.txt": b"hello"})
        self.assertEqual((place.name, book.kinds()["notebook"].label, notebook.pages), ("Notebook", "Notebook", {"front": {"a.txt": b"hello"}}))
        book.remove(place.id)
        self.assertEqual((book.places(), notebook.pages), ([], {}))


if __name__ == "__main__":
    unittest.main()
