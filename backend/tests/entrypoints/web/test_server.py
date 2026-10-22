import os
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from http.client import HTTPConnection, RemoteDisconnected
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
import time
from pathlib import Path
from unittest import mock
from urllib.parse import urlparse

from chronata.entrypoints.web import connection_owner
from chronata.entrypoints.web.address import HOST, page_key_name
from chronata.adapters.storage.owner_only_folder import NotPrivate, OwnerOnlyFolder
from chronata.entrypoints.web.door_proof import ANSWERED_BY_THE_PAGE, ASKED_BY_THE_DOOR, fresh_nonce, proof, proves
from chronata.entrypoints.web.page_door import PageDoor
from chronata.entrypoints.web.server import LARGEST_REQUEST, close, serve_in_background
from tests.fakes import FakeDesktop, Fixture

ANOTHER_USER = "nobody"
NO_ANSWER = 0


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
        except (RemoteDisconnected, ConnectionResetError):
            return Reply(NO_ANSWER, {}, b"")
        finally:
            connection.close()

    def key(self) -> str:
        return self.keys.read(page_key_name(self.port))

    def asked_by_the_door(self, key: str, nonce: str) -> dict:
        return {"X-Door-Nonce": nonce, "X-Door-Proof": proof(key, ASKED_BY_THE_DOOR, nonce)}

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
    def test_needs_proof_of_the_page_key(self):
        self.assertEqual(self.request("POST", "/door/code", self.asked_by_the_door("made-up", fresh_nonce())).status, 403)

    def test_never_needs_the_key_itself_to_be_sent(self):
        self.assertEqual(self.request("POST", "/door/code", {"X-Page-Key": self.key()}).status, 403)

    def test_is_answered_with_proof_that_the_page_holds_the_key(self):
        nonce = fresh_nonce()
        answer = json.loads(self.request("POST", "/door/code", self.asked_by_the_door(self.key(), nonce)).body)
        self.assertTrue(proves(self.key(), answer["proof"], ANSWERED_BY_THE_PAGE, nonce, answer["code"]))

    def test_is_refused_to_a_browser_even_with_the_key(self):
        reply = self.request("POST", "/door/code", self.asked_by_the_door(self.key(), fresh_nonce()) | {"Origin": self.origin})
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
        self.assertEqual(self.request("POST", "/door/code", self.asked_by_the_door(self.key(), fresh_nonce())).status, NO_ANSWER)

    def test_is_refused_even_with_a_leaked_visit(self):
        cookie, token = self.enter()
        self.from_this_user = False
        self.assertEqual(self.request("GET", "/", {"Cookie": cookie}).status, NO_ANSWER)
        self.assertEqual(self.request("GET", "/api/state", self.page_request(cookie, token)).status, NO_ANSWER)

    def test_cannot_open_the_door_with_a_leaked_launch_link(self):
        link = urlparse(self.launch_link())
        self.from_this_user = False
        self.assertEqual(self.request("GET", f"{link.path}?{link.query}").status, NO_ANSWER)


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
            return NO_ANSWER
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
            self.assertEqual(self.door_status(), NO_ANSWER)

    @unittest.skipUnless(subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode == 0,
                         "needs sudo; run `sudo -v` in a terminal, then the tests from the same terminal")
    def test_refuses_another_user_who_has_the_key(self):
        script = (
            "import hashlib, hmac, sys\nfrom http.client import HTTPConnection\n"
            "port, key, nonce = int(sys.argv[1]), sys.argv[2], 'n' * 43\n"
            "asked = {'X-Door-Nonce': nonce, 'X-Door-Proof': hmac.new(key.encode(), ('door\\n' + nonce).encode(), hashlib.sha256).hexdigest()}\n"
            "replies = []\n"
            "for method, path, headers in (('GET', '/', {}), ('POST', '/door/code', asked)):\n"
            "    connection = HTTPConnection('127.0.0.1', port, timeout=5)\n"
            "    try:\n"
            "        connection.request(method, path, headers=headers)\n"
            "        replies.append(str(connection.getresponse().status))\n"
            "    except Exception:\n"
            "        replies.append('closed')\n"
            "print(' '.join(replies))\n"
        )
        key = self.keys.read(page_key_name(self.port))
        run = subprocess.run(["sudo", "-n", "-u", ANOTHER_USER, sys.executable, "-I", "-c", script, str(self.port), key],
                             capture_output=True, text=True, cwd="/")
        self.assertEqual(run.stdout.strip(), "closed closed", run.stderr)


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
    def test_says_so_and_drops_a_key_left_behind(self):
        desktop, port = FakeDesktop(), free_port()
        keys = OwnerOnlyFolder(Path(tempfile.mkdtemp()) / "chronata")
        keys.write(page_key_name(port), "made-up stale key")
        PageDoor(desktop, port, keys).open()
        self.assertEqual((desktop.opened, desktop.notices[0][0], keys.read(page_key_name(port))), ([], "Chronata's page is not running", None))

    def test_says_so_and_opens_nothing(self):
        desktop = FakeDesktop()
        PageDoor(desktop, free_port(), OwnerOnlyFolder(Path(tempfile.mkdtemp()) / "chronata")).open()
        self.assertEqual((desktop.opened, desktop.notices[0][0]), ([], "Chronata's page is not running"))


class TheDoorFacingAnImpostor(unittest.TestCase):
    def setUp(self):
        class Impostor(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.dumps({"code": "made-up-code", "proof": "0" * 64}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.impostor = HTTPServer((HOST, 0), Impostor)
        threading.Thread(target=self.impostor.serve_forever, daemon=True).start()
        self.port = self.impostor.server_port
        self.keys = OwnerOnlyFolder(Path(tempfile.mkdtemp()) / "chronata")
        self.keys.write(page_key_name(self.port), "made-up stale key")
        self.desktop = FakeDesktop()

    def tearDown(self):
        self.impostor.shutdown()
        self.impostor.server_close()

    def test_that_cannot_prove_it_holds_the_key_opens_nothing(self):
        PageDoor(self.desktop, self.port, self.keys).open()
        self.assertEqual((self.desktop.opened, self.desktop.notices[0][0]), ([], "Chronata will not open its page"))

    def test_on_a_port_held_by_another_user_is_not_even_asked(self):
        PageDoor(self.desktop, self.port, self.keys, listener_owner=lambda address: os.getuid() + 1).open()
        self.assertEqual((self.desktop.opened, self.desktop.notices[0][0]), ([], "Chronata will not open its page"))


class AConnectionThatSaysNothing(ServedPage):
    def test_does_not_hold_up_anyone_else(self):
        with socket.create_connection((HOST, self.port)):
            started = time.monotonic()
            self.assertEqual(self.request("GET", "/").status, 401)
            self.assertLess(time.monotonic() - started, 2)


class AnOversizedRequest(ServedPage):
    def test_is_refused_before_it_is_read(self):
        cookie, token = self.enter()
        headers = self.page_request(cookie, token, self.origin) | {"Content-Length": str(LARGEST_REQUEST + 1)}
        connection = HTTPConnection(HOST, self.port, timeout=5)
        connection.putrequest("POST", "/api/save")
        for name, value in headers.items():
            connection.putheader(name, value)
        connection.endheaders()
        self.assertEqual(connection.getresponse().status, 413)
        connection.close()


class ClosingThePage(ServedPage):
    def test_forgets_its_key(self):
        close(self.server, self.keys)
        self.assertIsNone(self.keys.read(page_key_name(self.port)))
        self.server = serve_in_background(self.f.app, self.port, self.owner_check(), self.keys)


class CheckingTheLogWithoutOpenssl(ServedPage):
    def test_says_why_instead_of_dropping_the_connection(self):
        from chronata.use_cases.log.ports import CannotCheck
        cookie, token = self.enter()
        with mock.patch.object(self.f.app.timestamper, "problems", side_effect=CannotCheck("openssl is not installed")):
            reply = self.request("GET", "/api/verify", self.page_request(cookie, token))
        self.assertEqual((reply.status, json.loads(reply.body)["error"]), (503, "openssl is not installed"))


class StoppingChronataUi(unittest.TestCase):
    def test_removes_its_key(self):
        import signal
        home, port = Path(tempfile.mkdtemp()), free_port()
        environment = {**os.environ, "CHRONATA_HOME": str(home / "data"), "CHRONATA_CONFIG": str(home / "config"), "XDG_RUNTIME_DIR": str(home / "run")}
        launcher = Path(__file__).parents[3] / "bin" / "chronata"
        running = subprocess.Popen([str(launcher), "ui", "--no-browser", "--port", str(port)], env=environment, stdout=subprocess.DEVNULL)
        key = home / "run" / "chronata" / page_key_name(port)
        for _ in range(100):
            if key.exists():
                break
            time.sleep(0.05)
        running.send_signal(signal.SIGTERM)
        running.wait(timeout=10)
        self.assertEqual((running.returncode, key.exists()), (0, False))

if __name__ == "__main__":
    unittest.main()
