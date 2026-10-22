import os
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest import mock
from urllib.parse import urlparse

from chronata.entrypoints.web import connection_owner
from chronata.entrypoints.web.address import HOST, page_key_name
from chronata.entrypoints.web.owner_only_folder import NotPrivate, OwnerOnlyFolder
from chronata.entrypoints.web.page_door import PageDoor
from chronata.entrypoints.web.server import serve_in_background
from tests.fakes import FakeDesktop, Fixture

ANOTHER_USER = "nobody"


def free_port() -> int:
    with socket.create_server((HOST, 0)) as probe:
        return probe.getsockname()[1]


class Reply:
    def __init__(self, status: int, headers: dict, body: bytes):
        self.status = status
        self.headers = headers
        self.body = body


class ServedPage(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()
        self.port = free_port()
        self.keys = OwnerOnlyFolder(Path(tempfile.mkdtemp()) / "chronata")
        self.from_this_user = True
        self.server = serve_in_background(self.f.app, self.port, self.owner_check(), self.keys)
        self.origin = f"http://{HOST}:{self.port}"

    def owner_check(self):
        return lambda client, server: self.from_this_user

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def request(self, method: str, path: str, headers: dict | None = None, body: bytes | None = None) -> Reply:
        connection = HTTPConnection(HOST, self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            reply = connection.getresponse()
            return Reply(reply.status, dict(reply.getheaders()), reply.read())
        finally:
            connection.close()

    def key(self) -> str:
        return self.keys.read(page_key_name(self.port))

    def launch_link(self) -> str:
        desktop = FakeDesktop()
        PageDoor(desktop, self.port, self.keys).open("clock-in")
        return desktop.opened[0]

    def enter(self) -> tuple[str, str]:
        link = urlparse(self.launch_link())
        cookie = self.request("GET", f"{link.path}?{link.query}").headers["Set-Cookie"].split(";")[0]
        page = self.request("GET", "/", {"Cookie": cookie}).body.decode()
        return cookie, page.split('name="token" content="')[1].split('"')[0]

    def page_request(self, cookie: str, token: str, origin: str | None = None) -> dict:
        headers = {"Cookie": cookie, "X-Token": token, "Content-Type": "application/json"}
        return headers | ({"Origin": origin} if origin else {})


class WithoutAVisit(ServedPage):
    def test_the_page_shows_only_the_locked_notice_and_no_token(self):
        reply = self.request("GET", "/")
        self.assertEqual(reply.status, 401)
        self.assertIn(b"only opens for the person whose log it is", reply.body)
        self.assertNotIn(b'name="token"', reply.body)

    def test_the_pages_scripts_are_not_handed_out(self):
        self.assertEqual(self.request("GET", "/main.js").status, 401)

    def test_the_log_cannot_be_read(self):
        self.assertEqual(self.request("GET", "/api/state").status, 401)

    def test_a_backup_place_cannot_be_added(self):
        reply = self.request("POST", "/api/places/add", {"Origin": self.origin}, b'{"kind": "folder"}')
        self.assertEqual(reply.status, 401)


class OpeningThroughTheDoor(ServedPage):
    def test_the_link_opens_the_page_at_the_asked_section(self):
        link = urlparse(self.launch_link())
        self.assertEqual((link.path, link.fragment), ("/door", "clock-in"))
        reply = self.request("GET", f"{link.path}?{link.query}")
        self.assertEqual((reply.status, reply.headers["Location"]), (303, "/"))

    def test_the_visit_cookie_is_hidden_from_scripts_and_other_sites(self):
        link = urlparse(self.launch_link())
        cookie = self.request("GET", f"{link.path}?{link.query}").headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)

    def test_with_the_visit_the_page_and_the_log_open(self):
        cookie, token = self.enter()
        self.assertEqual(self.request("GET", "/main.js", {"Cookie": cookie}).status, 200)
        self.assertEqual(self.request("GET", "/api/state", self.page_request(cookie, token)).status, 200)

    def test_a_launch_link_works_only_once(self):
        link = urlparse(self.launch_link())
        self.request("GET", f"{link.path}?{link.query}")
        self.assertEqual(self.request("GET", f"{link.path}?{link.query}").status, 401)

    def test_the_page_cannot_be_framed_or_sniffed(self):
        cookie, _ = self.enter()
        headers = self.request("GET", "/", {"Cookie": cookie}).headers
        self.assertEqual((headers["X-Frame-Options"], headers["X-Content-Type-Options"]), ("DENY", "nosniff"))
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])


class AskingForALaunchCode(ServedPage):
    def test_needs_the_page_key(self):
        self.assertEqual(self.request("POST", "/door/code", {"X-Page-Key": "made-up"}).status, 403)

    def test_is_refused_to_a_browser_even_with_the_key(self):
        reply = self.request("POST", "/door/code", {"X-Page-Key": self.key(), "Origin": self.origin})
        self.assertEqual(reply.status, 403)

    def test_the_key_is_kept_where_only_you_can_open_it(self):
        self.assertEqual(stat.S_IMODE(os.stat(self.keys.path / page_key_name(self.port)).st_mode), 0o600)


class ARelayRunningAsYou(ServedPage):
    def test_without_a_visit_reads_nothing(self):
        self.assertEqual(self.request("GET", "/api/state").status, 401)

    def test_with_a_stolen_cookie_but_no_form_token_reads_nothing(self):
        cookie, _ = self.enter()
        self.assertEqual(self.request("GET", "/api/state", {"Cookie": cookie}).status, 403)


class ChangesFromThePage(ServedPage):
    def test_are_refused_from_another_site(self):
        cookie, token = self.enter()
        reply = self.request("POST", "/api/places/remove", self.page_request(cookie, token, "http://made-up.example"), b'{"id": "x"}')
        self.assertEqual(reply.status, 403)

    def test_are_refused_without_saying_where_they_come_from(self):
        cookie, token = self.enter()
        self.assertEqual(self.request("POST", "/api/places/remove", self.page_request(cookie, token), b'{"id": "x"}').status, 403)

    def test_are_refused_when_the_browser_says_another_site_sent_them(self):
        cookie, token = self.enter()
        headers = self.page_request(cookie, token, self.origin) | {"Sec-Fetch-Site": "cross-site"}
        self.assertEqual(self.request("POST", "/api/places/remove", headers, b'{"id": "x"}').status, 403)

    def test_from_the_page_itself_reach_the_log(self):
        cookie, token = self.enter()
        reply = self.request("POST", "/api/places/remove", self.page_request(cookie, token, self.origin), b'{"id": "x"}')
        self.assertNotIn(reply.status, (401, 403))


class AnotherUsersConnection(ServedPage):
    def test_is_refused_a_launch_code_even_with_a_leaked_key(self):
        self.from_this_user = False
        self.assertEqual(self.request("POST", "/door/code", {"X-Page-Key": self.key()}).status, 403)

    def test_is_refused_even_with_a_leaked_visit(self):
        cookie, token = self.enter()
        self.from_this_user = False
        self.assertEqual(self.request("GET", "/", {"Cookie": cookie}).status, 403)
        self.assertEqual(self.request("GET", "/api/state", self.page_request(cookie, token)).status, 403)

    def test_cannot_open_the_door_with_a_leaked_launch_link(self):
        link = urlparse(self.launch_link())
        self.from_this_user = False
        self.assertEqual(self.request("GET", f"{link.path}?{link.query}").status, 403)


class AnotherHostName(ServedPage):
    def test_is_refused(self):
        self.assertEqual(self.request("GET", "/", {"Host": "made-up.example"}).status, 403)


class TheRealOwnerCheck(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()
        self.port = free_port()
        self.keys = OwnerOnlyFolder(Path(tempfile.mkdtemp()) / "chronata")
        self.server = serve_in_background(self.f.app, self.port, keys=self.keys)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def door_status(self) -> int:
        desktop = FakeDesktop()
        PageDoor(desktop, self.port, self.keys).open()
        if not desktop.opened:
            return 403
        link = urlparse(desktop.opened[0])
        connection = HTTPConnection(HOST, self.port, timeout=5)
        connection.request("GET", f"{link.path}?{link.query}")
        status = connection.getresponse().status
        connection.close()
        return status

    def test_lets_this_user_in(self):
        self.assertEqual(self.door_status(), 303)

    def test_refuses_everyone_when_it_cannot_tell_who_is_connecting(self):
        with mock.patch.object(connection_owner, "TCP_TABLE", Path("/nonexistent/tcp")):
            self.assertEqual(self.door_status(), 403)

    @unittest.skipUnless(subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode == 0,
                         "needs sudo; run `sudo -v` in a terminal, then the tests from the same terminal")
    def test_refuses_another_user_who_has_the_key(self):
        script = (
            "import sys\nfrom http.client import HTTPConnection\n"
            "port, key = int(sys.argv[1]), sys.argv[2]\n"
            "replies = []\n"
            "for method, path, headers in (('GET', '/', {}), ('POST', '/door/code', {'X-Page-Key': key})):\n"
            "    connection = HTTPConnection('127.0.0.1', port, timeout=5)\n"
            "    connection.request(method, path, headers=headers)\n"
            "    replies.append(str(connection.getresponse().status))\n"
            "print(' '.join(replies))\n"
        )
        key = self.keys.read(page_key_name(self.port))
        run = subprocess.run(["sudo", "-n", "-u", ANOTHER_USER, sys.executable, "-I", "-c", script, str(self.port), key],
                             capture_output=True, text=True, cwd="/")
        self.assertEqual(run.stdout.strip(), "403 403", run.stderr)


class StartingWithAKeyFolderOthersCanOpen(unittest.TestCase):
    def test_does_not_start_the_page(self):
        path = Path(tempfile.mkdtemp()) / "chronata"
        path.mkdir()
        path.chmod(0o755)
        port = free_port()
        with self.assertRaises(NotPrivate):
            serve_in_background(Fixture().app, port, keys=OwnerOnlyFolder(path))
        with socket.create_server((HOST, port)):
            pass


class TheDoorWithNothingRunning(unittest.TestCase):
    def test_says_so_and_opens_nothing(self):
        desktop = FakeDesktop()
        PageDoor(desktop, free_port(), OwnerOnlyFolder(Path(tempfile.mkdtemp()) / "chronata")).open()
        self.assertEqual((desktop.opened, desktop.notices[0][0]), ([], "Chronata's page is not running"))


if __name__ == "__main__":
    unittest.main()
