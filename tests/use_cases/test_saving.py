import tempfile
import unittest
from pathlib import Path

from chronata.use_cases.verification import verify
from chronata.wiring import open_saved_copy
from tests.fakes import Fixture


class SavingEverywhere(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T17:40:00")
        self.f.sheet.add("2026-10-13", "08:02:11", "17:31:40", "written later", "release prep")
        self.folder = Path(tempfile.mkdtemp())
        self.vault = Path(tempfile.mkdtemp())
        (self.vault / ".obsidian").mkdir()
        self.f.app.saving.add_place(self.f.sheet, "folder", "Text file", str(self.folder))
        self.f.app.saving.add_place(self.f.sheet, "obsidian", "Vault", str(self.vault))

    def test_each_place_gets_the_sealed_log_and_its_own_readable_copy(self):
        self.assertTrue((self.folder / "sealed" / "ledger.jsonl").exists())
        self.assertIn("Tuesday 13 October 2026", (self.folder / "Chronata time log.txt").read_text())
        self.assertIn("release prep", (self.vault / "Chronata" / "Days" / "2026-10-13.md").read_text())

    def test_a_saved_copy_checks_out_on_its_own(self):
        record, timestamper = open_saved_copy(self.vault)
        findings = verify(record, timestamper)
        self.assertEqual((findings.entries, findings.problems), (1, []))

    def test_a_missing_place_is_reported_and_others_still_save(self):
        for place, _ in self.f.app.saving.statuses():
            if place.kind == "folder":
                self.f.app.saving.remove_place(place.id)
        self.f.app.saving.places.add("folder", "Gone", str(self.folder))
        self.folder.rename(self.folder.with_name(self.folder.name + "-moved"))
        outcome = self.f.sheet.save_now()
        self.assertIn("not saved to Gone", outcome.warning)
        self.assertTrue((self.vault / "Chronata" / "sealed" / "ledger.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
