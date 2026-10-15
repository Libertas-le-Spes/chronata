import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chronata.adapters import this_machine
from chronata.adapters.desktop import linux_desktop
from chronata.adapters.desktop.linux_desktop import LinuxDesktop
from chronata.adapters.desktop.windows_desktop import WindowsDesktop
from chronata.adapters.power_history.last_log import LastLog
from chronata.adapters.power_history.systemd_journal import SystemdJournal
from chronata.adapters.power_history.windows_events import WindowsEvents


class ChoosingForThisMachine(unittest.TestCase):
    def test_windows_gets_its_own_desktop_and_event_log(self):
        self.assertIsInstance(this_machine.desktop("win32"), WindowsDesktop)
        self.assertIsInstance(this_machine.power_history("win32"), WindowsEvents)

    def test_linux_with_systemd_reads_the_journal(self):
        self.assertIsInstance(this_machine.power_history("linux", Path(tempfile.mkdtemp())), SystemdJournal)

    def test_linux_without_systemd_reads_the_login_records(self):
        self.assertIsInstance(this_machine.power_history("linux", Path(tempfile.mkdtemp()) / "absent"), LastLog)
        self.assertIsInstance(this_machine.desktop("linux"), LinuxDesktop)


class DialogsWithoutZenity(unittest.TestCase):
    def test_linux_falls_back_to_tk_for_both_questions(self):
        with mock.patch.object(linux_desktop.shutil, "which", return_value=None), \
             mock.patch.object(linux_desktop.tk_dialogs, "ask", return_value="Northwind") as ask, \
             mock.patch.object(linux_desktop.tk_dialogs, "choose", return_value="Use Northwind") as choose:
            desktop = LinuxDesktop()
            self.assertEqual(desktop.ask("Which label?", "Northwind"), "Northwind")
            self.assertEqual(desktop.choose("Sure?", ["Use Northwind"]), "Use Northwind")
        ask.assert_called_once_with("Chronata", "Which label?", "Northwind")
        choose.assert_called_once_with("Chronata", "Sure?", ["Use Northwind"])


if __name__ == "__main__":
    unittest.main()
