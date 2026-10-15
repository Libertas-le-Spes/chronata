import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chronata.use_cases.log.outcome import UserError
from tests.fakes import Fixture


class WithoutAGitPlace(unittest.TestCase):
    def test_no_git_is_used_or_needed(self):
        f = Fixture("2026-10-14T08:30:00")
        f.app.saving.add_place(f.app.log, "folder", "Text file", tempfile.mkdtemp())
        f.app.clocking.clock_in(None, None)
        self.assertFalse((f.data / ".git").exists())
        self.assertFalse(f.app.history.keeps_history())

    def test_without_git_installed_a_git_place_says_so(self):
        f = Fixture("2026-10-14T08:30:00")
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaisesRegex(UserError, "git is not installed"):
                f.app.saving.add_place(f.app.log, "git", "Backup", "/nowhere.git")


class AddingAGitPlaceLater(unittest.TestCase):
    def test_history_starts_then_and_everything_so_far_is_pushed(self):
        f = Fixture("2026-10-14T08:30:00")
        f.app.clocking.clock_in(None, None)
        f.at("2026-10-14T12:00:00")
        f.app.clocking.clock_out(None, None)
        backup = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(backup)], check=True)
        outcome = f.app.saving.add_place(f.app.log, "git", "Backup", str(backup))
        self.assertIsNone(outcome.warning)
        self.assertTrue(f.app.history.keeps_history())
        pushed = subprocess.run(["git", "-C", str(backup), "show", "main:ledger.jsonl"], capture_output=True, text=True).stdout
        self.assertEqual(len(pushed.splitlines()), 2)
        readme = subprocess.run(["git", "-C", str(backup), "show", "main:README.md"], capture_output=True, text=True).stdout
        self.assertIn("[No label]", readme)


if __name__ == "__main__":
    unittest.main()
