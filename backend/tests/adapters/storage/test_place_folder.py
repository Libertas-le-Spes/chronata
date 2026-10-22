import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from chronata.adapters.places.kinds.folder_place import FolderPlace, ObsidianVault
from chronata.adapters.places.place_book import PlaceBook
from chronata.adapters.places.save_record import SaveRecord
from chronata.adapters.places.transport.git_folder import GitFolders
from chronata.adapters.places.transport.git_transport import GitTransport
from chronata.adapters.storage.changed_files import WRITTEN_LIST
from chronata.adapters.storage.place_folder import PlaceFolder
from chronata.use_cases.log.ports import SaveError


def fresh() -> Path:
    return Path(tempfile.mkdtemp())


def saves() -> SaveRecord:
    return SaveRecord(fresh() / "saves.json")


class AFolderPlaceUnderAttack(unittest.TestCase):
    def setUp(self):
        self.home = fresh()
        self.keepsake = self.home / "keepsake.txt"
        self.keepsake.write_text("not Chronata's\n")
        self.shared = fresh()
        self.book = PlaceBook(fresh(), [FolderPlace(saves())])
        self.place = self.book.add("folder", "", str(self.shared))

    def test_names_planted_in_the_places_own_list_are_never_deleted(self):
        self.book.deliver(self.place, {"README.md": b"first"})
        with (self.shared / WRITTEN_LIST).open("a") as planted:
            planted.write(f"{self.keepsake}\n../{self.home.name}/keepsake.txt\nREADME.md\n")
        self.book.deliver(self.place, {"Days/2026-01-05.md": b"day"})
        self.assertEqual(self.keepsake.read_text(), "not Chronata's\n")

    def test_a_folder_swapped_for_a_link_is_not_followed(self):
        (self.shared / "Days").symlink_to(self.home)
        with self.assertRaisesRegex(SaveError, "is a link"):
            self.book.deliver(self.place, {"Days/keepsake.txt": b"overwritten"})
        self.assertEqual(self.keepsake.read_text(), "not Chronata's\n")

    def test_a_file_swapped_for_a_link_is_replaced_not_followed(self):
        (self.shared / "README.md").symlink_to(self.keepsake)
        self.book.deliver(self.place, {"README.md": b"chronata"})
        self.assertEqual((self.keepsake.read_text(), (self.shared / "README.md").is_symlink()), ("not Chronata's\n", False))

    def test_files_it_wrote_and_no_longer_writes_are_removed_with_their_emptied_folders(self):
        self.book.deliver(self.place, {"README.md": b"r", "Old Label/Days/2026-01-05.md": b"day"})
        self.book.deliver(self.place, {"README.md": b"r"})
        self.assertEqual(sorted(path.name for path in self.shared.iterdir()), ["README.md"])

    def test_what_it_writes_only_its_owner_can_open(self):
        self.book.deliver(self.place, {"Days/2026-01-05.md": b"day"})
        self.assertEqual(stat.S_IMODE(os.stat(self.shared / "Days" / "2026-01-05.md").st_mode), 0o600)


class AVaultUnderAttack(unittest.TestCase):
    def test_its_chronata_folder_swapped_for_a_link_is_not_followed(self):
        vault, elsewhere = fresh(), fresh()
        (vault / ".obsidian").mkdir()
        (vault / "Chronata").symlink_to(elsewhere)
        book = PlaceBook(fresh(), [ObsidianVault(saves())])
        with self.assertRaisesRegex(SaveError, "is a link"):
            book.deliver(book.add("obsidian", "", str(vault)), {"README.md": b"r"})
        self.assertEqual(list(elsewhere.iterdir()), [])


class NamesThatLeaveThePlace(unittest.TestCase):
    def test_are_refused(self):
        folder = PlaceFolder(fresh())
        for name in ("../outside.txt", "/tmp/outside.txt", "a/../../outside.txt", "", "a\0b"):
            with self.subTest(name=name), self.assertRaises(SaveError):
                folder.write(name, b"x")


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


class AGitFolderUnderAttack(unittest.TestCase):
    def setUp(self):
        self.remote = fresh() / "notes.git"
        git("init", "-q", "--bare", "-b", "main", str(self.remote), cwd=Path("/"))
        self.collaborator = fresh()
        git("clone", "-q", str(self.remote), ".", cwd=self.collaborator)
        (self.collaborator / "Notes").mkdir()
        (self.collaborator / "Notes" / "note.md").write_text("theirs\n")
        self.commit("start")
        self.copies = fresh()
        self.folders = GitFolders(self.copies, saves(), GitTransport(local_allowed=True))
        self.ledger = self.copies.parent / f"{self.copies.name}-ledger.jsonl"
        self.ledger.write_text("sealed entries\n")

    def commit(self, message: str) -> None:
        git("add", "-A", cwd=self.collaborator)
        git("commit", "-q", "-m", message, cwd=self.collaborator)
        git("push", "-q", "origin", "main", cwd=self.collaborator)

    def test_a_pushed_list_naming_files_outside_deletes_nothing(self):
        self.folders.save("p1", str(self.remote), "Work Logs", {"README.md": b"first"})
        git("pull", "-q", cwd=self.collaborator)
        with (self.collaborator / "Work Logs" / WRITTEN_LIST).open("a") as planted:
            planted.write(f"../../{self.ledger.name}\n{self.ledger}\n")
        self.commit("tidy")
        self.folders.save("p1", str(self.remote), "Work Logs", {"README.md": b"second"})
        self.assertEqual(self.ledger.read_text(), "sealed entries\n")

    def test_a_pushed_link_in_place_of_a_folder_is_refused(self):
        self.folders.save("p1", str(self.remote), "Work Logs", {"README.md": b"first"})
        git("pull", "-q", cwd=self.collaborator)
        (self.collaborator / "Work Logs" / "Days").symlink_to(self.copies.parent)
        self.commit("link")
        with self.assertRaisesRegex(SaveError, "is a link"):
            self.folders.save("p1", str(self.remote), "Work Logs", {"README.md": b"first", "Days/x.md": b"day"})
        self.assertFalse((self.copies.parent / "x.md").exists())


if __name__ == "__main__":
    unittest.main()
