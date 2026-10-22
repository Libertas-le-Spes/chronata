import subprocess
import threading
import unittest
from unittest import mock

from chronata.adapters.desktop import linux_desktop
from chronata.adapters.desktop.kdialog import KDialog
from chronata.adapters.desktop.linux_desktop import LinuxDesktop
from chronata.adapters.desktop.zenity import Zenity


def answering(stdout: str, returncode: int = 0):
    return mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], returncode, stdout, ""))


class Notifications(unittest.TestCase):
    def sent(self, *notification) -> list[str]:
        with answering("") as run, mock.patch.object(linux_desktop.shutil, "which", return_value="/usr/bin/notify-send"):
            LinuxDesktop().notify(*notification)
            [thread.join() for thread in threading.enumerate() if thread is not threading.current_thread() and thread.daemon]
        return run.call_args.args[0]

    def test_a_question_stays_on_screen_until_it_is_answered(self):
        self.assertIn("--urgency=critical", self.sent("Lunch time", "Clocking out for lunch?", lambda: None, "Clock out for lunch"))

    def test_an_announcement_goes_away_on_its_own(self):
        self.assertNotIn("--urgency=critical", self.sent("Clocked in", ""))

    def test_text_is_never_read_as_an_option_or_as_markup(self):
        for notification in (("--help", "<b>made-up</b> & more"), ("--help", "<b>made-up</b> & more", lambda: None, "Open")):
            sent = self.sent(*notification)
            self.assertEqual(sent[-3:], ["--", "--help", "&lt;b&gt;made-up&lt;/b&gt; &amp; more"])


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
        with answering("0\n") as run:
            self.assertEqual(KDialog().choose("Chronata", "Sure?", ["Use Northwind", "Clock in on Acme"]), "Use Northwind")
        self.assertEqual(run.call_args.args[0],
                         ["kdialog", "--title", "Chronata", "--menu", "Sure?", "0", "Use Northwind", "1", "Clock in on Acme"])

    def test_a_choice_that_starts_with_a_dash_can_still_be_picked(self):
        with answering("1\n"):
            self.assertEqual(KDialog().choose("Chronata", "Which?", ["Acme", "-Made-up"]), "-Made-up")

    def test_cancelling_the_menu_is_no_answer(self):
        with answering("", 1):
            self.assertIsNone(KDialog().choose("Chronata", "Sure?", ["Use Northwind"]))


if __name__ == "__main__":
    unittest.main()
