import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chronata.adapters.places.addresses import checked_git_address, checked_web_address, shown
from chronata.adapters.places.kinds.webdav_place import WebDavServer
from chronata.adapters.places.place_book import PlaceBook
from chronata.adapters.places.save_record import SaveRecord
from chronata.adapters.secrets.secret_service import SecretService
from chronata.use_cases.log.ports import SaveError
from tests.fakes import FakeSecrets

PACKAGE = Path(__file__).parents[3] / "chronata"


class WebServerAddresses(unittest.TestCase):
    def test_only_https_without_a_name_or_password_in_it_is_accepted(self):
        self.assertEqual(checked_web_address(" https://cloud.example.com/dav/ "), "https://cloud.example.com/dav/")
        for refused in ("http://cloud.example.com/dav/", "https://alice:made-up@cloud.example.com/", "https://alice@cloud.example.com/",
                        "-https://x", "ftp://cloud.example.com", "https://", "https://cloud.example.com/a b"):
            with self.subTest(address=refused), self.assertRaises(SaveError):
                checked_web_address(refused)


class GitAddresses(unittest.TestCase):
    def test_only_https_and_ssh_are_accepted(self):
        for accepted in ("https://git.example.com/me/log.git", "ssh://git@git.example.com/me/log.git", "git@git.example.com:me/log.git",
                         "work-alias:me/log.git", "/media/usb/log.git", "file:///media/usb/log.git", "git@git.example.com:/srv/log.git"):
            self.assertEqual(checked_git_address(accepted), accepted)

    def test_addresses_git_would_read_as_options_or_commands_are_refused(self):
        for refused in ("--upload-pack=touch /tmp/made-up", "-oProxyCommand=made-up", "ext::sh -c made-up", "fd::17",
                        "https://alice:made-up-token@git.example.com/me/log.git", "git@git.example.com:-oProxyCommand=x",
                        "ssh://git:made-up@git.example.com/me/log.git", "http://git.example.com/me/log.git", "git://git.example.com/log.git",
                        "relative/repo", "https:////x"):
            with self.subTest(address=refused), self.assertRaises(SaveError):
                checked_git_address(refused)

    def test_credentials_are_never_shown(self):
        self.assertEqual(shown("https://alice:made-up-token@git.example.com/log.git"), "https://git.example.com/log.git")


class WebServerPasswords(unittest.TestCase):
    def setUp(self):
        self.settings = Path(tempfile.mkdtemp())
        self.secrets = FakeSecrets()
        self.kind = WebDavServer(SaveRecord(self.settings / "saves.json"), self.secrets)
        self.book = PlaceBook(self.settings, [self.kind])

    def test_go_to_the_keyring_and_never_into_the_place_list(self):
        place = self.book.add("webdav", "", "https://cloud.example.com/dav/", "alice", "made-up-password")
        self.assertEqual(self.secrets.kept, {place.id: "made-up-password"})
        self.assertNotIn("made-up-password", self.book.path.read_text())

    def test_leave_the_keyring_with_the_place(self):
        place = self.book.add("webdav", "", "https://cloud.example.com/dav/", "alice", "made-up-password")
        self.book.remove(place.id)
        self.assertEqual(self.secrets.kept, {})

    def test_missing_from_the_keyring_stops_the_save_instead_of_sending_nothing(self):
        place = self.book.add("webdav", "", "https://cloud.example.com/dav/", "alice", "made-up-password")
        self.secrets.kept.clear()
        with self.assertRaisesRegex(SaveError, "not in the desktop keyring"):
            self.book.deliver(place, {"a.txt": b"x"})

    def older_version_kept(self) -> None:
        self.book.path.write_text(json.dumps([{"id": "webdav-1", "kind": "webdav", "name": "Old", "target": "https://cloud.example.com/",
                                               "username": "alice", "password": "made-up-password", "folder": ""}]))

    def test_kept_in_plain_text_by_an_older_version_move_into_the_keyring(self):
        self.older_version_kept()
        PlaceBook(self.settings, [self.kind])
        self.assertEqual((self.secrets.kept, "password" in self.book.path.read_text()), ({"webdav-1": "made-up-password"}, False))

    def test_kept_in_plain_text_stay_where_they_are_until_the_keyring_takes_them(self):
        self.older_version_kept()
        with mock.patch.object(self.secrets, "keep", side_effect=SaveError("locked")):
            PlaceBook(self.settings, [self.kind])
        self.assertIn("made-up-password", self.book.path.read_text())
        PlaceBook(self.settings, [self.kind])
        self.assertEqual(self.secrets.kept, {"webdav-1": "made-up-password"})


class TheKeyring(unittest.TestCase):
    def stub(self, script: str) -> Path:
        folder = Path(tempfile.mkdtemp())
        (folder / "secret-tool").write_text(script)
        (folder / "secret-tool").chmod(0o700)
        return folder

    def test_receives_the_password_on_its_input_never_in_its_arguments(self):
        log = Path(tempfile.mkdtemp()) / "log"
        folder = self.stub(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{log}"\ncat >> "{log}"\n')
        with mock.patch.dict(os.environ, {"PATH": f"{folder}:{os.environ['PATH']}"}):
            SecretService().keep("webdav-1", "made-up-password")
        arguments, given = log.read_text().split("\n", 1)
        self.assertEqual(("made-up-password" in arguments, given), (False, "made-up-password"))

    def test_without_secret_tool_nothing_is_kept_and_it_says_why(self):
        with mock.patch.dict(os.environ, {"PATH": tempfile.mkdtemp()}), self.assertRaisesRegex(SaveError, "secret-tool"):
            SecretService().keep("webdav-1", "made-up-password")


class TheCommandLine(unittest.TestCase):
    def test_never_takes_a_password_as_an_argument_others_could_read(self):
        found = [str(path) for path in PACKAGE.rglob("*.py") if re.search(r"add_argument\([^)]*--pass", path.read_text())]
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
