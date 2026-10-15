import tempfile
import unittest
from pathlib import Path

from chronata.adapters import this_machine
from chronata.adapters.power.last_log import LastLog
from chronata.adapters.power.systemd_journal import SystemdJournal


class ChoosingForThisMachine(unittest.TestCase):
    def test_with_systemd_it_reads_the_journal(self):
        self.assertIsInstance(this_machine.power_history(Path(tempfile.mkdtemp())), SystemdJournal)

    def test_without_systemd_it_reads_the_login_records(self):
        self.assertIsInstance(this_machine.power_history(Path(tempfile.mkdtemp()) / "absent"), LastLog)


if __name__ == "__main__":
    unittest.main()
