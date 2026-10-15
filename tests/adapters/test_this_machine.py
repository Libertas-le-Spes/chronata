import base64
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chronata.adapters import this_machine
from chronata.adapters.desktop import linux_desktop, windows_forms
from chronata.adapters.desktop.kdialog import KDialog
from chronata.adapters.desktop.linux_desktop import LinuxDesktop
from chronata.adapters.desktop.windows_desktop import WindowsDesktop
from chronata.adapters.desktop.windows_forms import WindowsForms
from chronata.adapters.desktop.zenity import Zenity
from chronata.adapters.power_history.last_log import LastLog
from chronata.adapters.power_history.systemd_journal import SystemdJournal
from chronata.adapters.power_history.windows_events import WindowsEvents


def answering(stdout: str, returncode: int = 0):
    return mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], returncode, stdout, ""))


class ChoosingForThisMachine(unittest.TestCase):
    def test_windows_gets_its_own_desktop_and_event_log(self):
        self.assertIsInstance(this_machine.desktop("win32"), WindowsDesktop)
        self.assertIsInstance(this_machine.power_history("win32"), WindowsEvents)

    def test_linux_with_systemd_reads_the_journal(self):
        self.assertIsInstance(this_machine.power_history("linux", Path(tempfile.mkdtemp())), SystemdJournal)

    def test_linux_without_systemd_reads_the_login_records(self):
        self.assertIsInstance(this_machine.power_history("linux", Path(tempfile.mkdtemp()) / "absent"), LastLog)
        self.assertIsInstance(this_machine.desktop("linux"), LinuxDesktop)


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


class WindowsForms_(unittest.TestCase):
    def test_powershell_draws_the_choice_with_the_question_and_options_handed_over(self):
        with answering("Clock in on Acme") as run:
            picked = WindowsForms().choose("Chronata", "Today is a workday?", ["Use Northwind", "Clock in on Acme"])
        command, settings = run.call_args.args[0], run.call_args.kwargs
        self.assertEqual(picked, "Clock in on Acme")
        self.assertEqual(command[:5], ["powershell", "-NoProfile", "-NonInteractive", "-Sta", "-EncodedCommand"])
        self.assertEqual(base64.b64decode(command[5]).decode("utf-16-le"), windows_forms.script_for(["window.ps1", "choose.ps1"]))
        self.assertEqual((settings["env"]["CHRONATA_QUESTION"], settings["env"]["CHRONATA_OPTIONS"]),
                         ("Today is a workday?", "Use Northwind\nClock in on Acme"))

    def test_closing_the_form_is_no_answer(self):
        with answering("", 1):
            self.assertIsNone(WindowsForms().ask("Chronata", "Which label?", "Northwind"))

    def test_without_powershell_there_is_no_answer_rather_than_a_crash(self):
        with mock.patch("subprocess.run", side_effect=FileNotFoundError("powershell")):
            self.assertIsNone(WindowsForms().ask("Chronata", "Which label?", "Northwind"))


if __name__ == "__main__":
    unittest.main()
