import tempfile
import unittest
from pathlib import Path

from chronata.adapters.history.git_history import GitHistory


class HistoryInGit(unittest.TestCase):
    def test_rewriting_a_saved_line_shows_up_in_history(self):
        folder = Path(tempfile.mkdtemp())
        history = GitHistory(folder, "ledger.jsonl")
        for content in ("first\n", "first\nsecond\n"):
            (folder / "ledger.jsonl").write_text(content)
            history.commit("save")
        self.assertEqual(history.rewrites(), [])
        (folder / "ledger.jsonl").write_text("FIRST\nsecond\n")
        history.commit("rewrite")
        self.assertEqual(len(history.rewrites()), 1)


if __name__ == "__main__":
    unittest.main()
