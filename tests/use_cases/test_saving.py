import tempfile
import unittest
from pathlib import Path

from chronata.use_cases.verification import verify
from chronata.wiring import open_saved_copy
from tests.fakes import Fixture


class SavingEverywhere(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T17:40:00")
        self.f.app.labels.create("Northwind", "08:00 to 17:00", "12:00 for 60 min")
        self.f.app.corrections.add("2026-10-13", "08:02:11", "17:31:40", "written later", "release prep", "Northwind")
        self.f.app.corrections.add("2026-10-14", "06:00", "07:00", "written later", None)
        self.folder = Path(tempfile.mkdtemp())
        self.vault = Path(tempfile.mkdtemp())
        (self.vault / ".obsidian").mkdir()
        self.f.app.saving.add_place(self.f.app.log, "folder", "Text file", str(self.folder))
        self.f.app.saving.add_place(self.f.app.log, "obsidian", "Vault", str(self.vault))

    def test_every_place_and_the_log_folder_get_a_folder_per_label(self):
        for where in (self.folder, self.vault / "Chronata", self.f.data):
            self.assertIn("release prep", (where / "Northwind" / "Days" / "2026-10-13.md").read_text())
            self.assertIn("Tuesday 13 October 2026", (where / "Northwind" / "Chronata time log.md").read_text())
            self.assertTrue((where / "No label" / "Days" / "2026-10-14.md").exists())
            self.assertIn("[Northwind]", (where / "README.md").read_text())
        self.assertTrue((self.folder / "sealed" / "ledger.jsonl").exists())

    def test_relabelling_moves_the_note_and_removes_the_old_one(self):
        unlabelled = next(s for s in self.f.app.log.shifts() if not s.label)
        self.f.app.labels.label_shift(unlabelled.id, "Northwind")
        self.assertTrue((self.folder / "Northwind" / "Days" / "2026-10-14.md").exists())
        self.assertFalse((self.folder / "No label").exists())

    def test_a_saved_copy_checks_out_on_its_own(self):
        record, timestamper = open_saved_copy(self.vault)
        findings = verify(record, timestamper)
        self.assertEqual((findings.entries, findings.problems), (2, []))

    def test_a_missing_place_is_reported_and_others_still_save(self):
        for place, _ in self.f.app.saving.statuses():
            if place.kind == "folder":
                self.f.app.saving.remove_place(place.id)
        self.f.app.saving.places.add("folder", "Gone", str(self.folder))
        self.folder.rename(self.folder.with_name(self.folder.name + "-moved"))
        outcome = self.f.app.log.save_now()
        self.assertIn("not saved to Gone", outcome.warning)
        self.assertTrue((self.vault / "Chronata" / "sealed" / "ledger.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
