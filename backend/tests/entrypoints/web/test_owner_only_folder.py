import os
import stat
import tempfile
import unittest
from pathlib import Path

from chronata.entrypoints.web.owner_only_folder import NotPrivate, OwnerOnlyFolder


def mode(path: Path) -> int:
    return stat.S_IMODE(os.lstat(path).st_mode)


class AnOwnerOnlyFolder(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "chronata"
        self.folder = OwnerOnlyFolder(self.path)

    def test_keeps_what_it_is_given_where_only_you_can_open_it(self):
        self.folder.write("page-key-1", "made-up key")
        self.assertEqual(self.folder.read("page-key-1"), "made-up key")
        self.assertEqual((mode(self.path), mode(self.path / "page-key-1")), (0o700, 0o600))

    def test_has_nothing_to_give_before_anything_is_written(self):
        self.path.mkdir(mode=0o700)
        self.assertIsNone(self.folder.read("page-key-1"))

    def test_will_not_write_into_a_folder_others_can_open(self):
        self.path.mkdir(mode=0o755)
        self.path.chmod(0o755)
        with self.assertRaises(NotPrivate):
            self.folder.write("page-key-1", "made-up key")

    def test_will_not_read_from_a_folder_others_can_open(self):
        self.folder.write("page-key-1", "made-up key")
        self.path.chmod(0o755)
        with self.assertRaises(NotPrivate):
            self.folder.read("page-key-1")

    def test_will_not_read_a_key_others_can_open(self):
        self.folder.write("page-key-1", "made-up key")
        (self.path / "page-key-1").chmod(0o644)
        with self.assertRaises(NotPrivate):
            self.folder.read("page-key-1")

    def test_will_not_follow_a_link_put_in_place_of_the_key(self):
        self.folder.write("elsewhere", "made-up key")
        (self.path / "page-key-1").symlink_to(self.path / "elsewhere")
        with self.assertRaises(NotPrivate):
            self.folder.read("page-key-1")

    def test_will_not_use_a_link_put_in_place_of_the_folder(self):
        real = Path(tempfile.mkdtemp())
        self.path.symlink_to(real)
        with self.assertRaises(NotPrivate):
            self.folder.write("page-key-1", "made-up key")


if __name__ == "__main__":
    unittest.main()
