import unittest

from chronata.adapters.storage import changed_files, data_folder
from chronata.presenters.readable_copy.readable_copy import KEPT_BESIDE_LABELS, label_folder
from chronata.timekeeping.labels.labels import tidy


class LabelFolders(unittest.TestCase):
    def test_never_take_the_name_of_something_chronata_keeps_beside_them(self):
        for kept in ("README.md", "ledger.jsonl", "Timestamps", "sealed", ".git", ".chronata-files"):
            with self.subTest(kept=kept):
                self.assertEqual(label_folder(kept), f"{kept.lstrip('.')} (label)")

    def test_know_every_name_the_data_folder_keeps(self):
        kept = {data_folder.LEDGER, data_folder.RULES, data_folder.TIMESTAMPS, data_folder.CHECKED_RECEIPTS, changed_files.WRITTEN_LIST.lstrip(".")}
        self.assertLessEqual({name.casefold() for name in kept}, {name.casefold() for name in KEPT_BESIDE_LABELS})

    def test_hold_no_control_characters(self):
        self.assertEqual(label_folder("Acme\x00\n Test"), "Acme- Test")


class TypedLabels(unittest.TestCase):
    def test_lose_invisible_and_control_characters(self):
        self.assertEqual(tidy("Ac\x00me‮ Test​ "), "Acme Test")


if __name__ == "__main__":
    unittest.main()
