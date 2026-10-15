import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chronata.adapters import this_machine
from chronata.adapters.desktop import linux_desktop
from chronata.adapters.desktop.kdialog import KDialog
from chronata.adapters.desktop.linux_desktop import LinuxDesktop
from chronata.adapters.desktop.zenity import Zenity
from chronata.adapters.power_history.last_log import LastLog
from chronata.adapters.power_history.systemd_journal import SystemdJournal


def answering(stdout: str, returncode: int = 0):
    return mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], returncode, stdout, ""))


class ChoosingForThisMachine(unittest.TestCase):
    def test_with_systemd_it_reads_the_journal(self):
        self.assertIsInstance(this_machine.power_history(Path(tempfile.mkdtemp())), SystemdJournal)

    def test_without_systemd_it_reads_the_login_records(self):
        self.assertIsInstance(this_machine.power_history(Path(tempfile.mkdtemp()) / "absent"), LastLog)


class LinuxDialogTools(unittest.TestCase):
    def desktop_with(self, *installed: str) -> LinuxDesktop:
        with mock.patch.object(linux_desktop.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}" if name in installed else None):
            return LinuxDesktop()

    def test_zenity_is_used_first(self):
        self.assertIsInstance(self.desktop_with("zenity", "kdialog").dialogs, Zenity)

    def test_kdialog_is_used_when_zenity_is_missing(self):
        self.assertIsInstance(self.desktop_with("kdialog").dialogs, KDialog)

    def test_with_neither_it_says_it_cannot_ask(self):
        desktop = self.desktop_with()
        self.assertFalse(desktop.can_ask())
        self.assertIsNone(desktop.ask("Which label?", "Northwind"))


class Zenity_(unittest.TestCase):
    def test_cancel_is_no_answer(self):
        with answering("Cancel\n", 1):
            self.assertIsNone(Zenity().choose("Chronata", "Sure?", ["Use Northwind"]))

    def test_an_empty_answer_means_no_label_and_closing_means_no_answer(self):
        with answering("\n"):
            self.assertEqual(Zenity().ask("Chronata", "Which label?", "Northwind"), "")
        with answering("", 1):
            self.assertIsNone(Zenity().ask("Chronata", "Which label?", "Northwind"))


class KDialog_(unittest.TestCase):
    def test_choices_are_offered_as_a_menu_and_the_chosen_one_comes_back(self):
        with answering("Use Northwind\n") as run:
            self.assertEqual(KDialog().choose("Chronata", "Sure?", ["Use Northwind", "Clock in on Acme"]), "Use Northwind")
        self.assertEqual(run.call_args.args[0],
                         ["kdialog", "--title", "Chronata", "--menu", "Sure?", "Use Northwind", "Use Northwind", "Clock in on Acme", "Clock in on Acme"])

    def test_cancelling_the_menu_is_no_answer(self):
        with answering("", 1):
            self.assertIsNone(KDialog().choose("Chronata", "Sure?", ["Use Northwind"]))


if __name__ == "__main__":
    unittest.main()
