import json
import re
import secrets
import signal
import sys
import threading
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qsl, urlparse

from chronata.entrypoints.web import requests
from chronata.entrypoints.web.address import HOST, page_key_name, page_url
from chronata.entrypoints.web.connection_owner import owned_by_this_user
from chronata.entrypoints.web.door_proof import ANSWERED_BY_THE_PAGE, ASKED_BY_THE_DOOR, proof, proves
from chronata.entrypoints.web.page_door import DOOR_PATH, LAUNCH_CODE_PATH, PageDoor
from chronata.entrypoints.web.refusals import refusal
from chronata.entrypoints.web.visits import Visit, Visits
from chronata.use_cases.log.ports import PrivateFolder

PAGE_FILE = re.compile(r"^/([a-z_]+/)?[a-z_]+\.(js|css)$")
CONTENT_TYPES = {"js": "text/javascript", "css": "text/css"}
HTML = "text/html; charset=utf-8"
LARGEST_REQUEST = 1024 * 1024
IDLE_SECONDS = 10
OPEN_AGAIN = "Open Chronata again from the bar, the applications menu or the chronata command."
SAFETY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}

OwnerCheck = Callable[[tuple[str, int], tuple[str, int]], bool]


def serve(app, port: int, open_browser: bool) -> None:
    server = _bind(app, port, owned_by_this_user, app.running)
    print(f"chronata at {page_url(port)} (Ctrl+C to stop)" if server else f"already running at {page_url(port)}")
    if server is None:
        if open_browser:
            PageDoor(app.desktop, port, app.running).open()
        return
    for stopping in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(stopping, lambda signum, frame: sys.exit(0))
    serving = threading.Thread(target=server.serve_forever, daemon=True)
    serving.start()
    if open_browser:
        PageDoor(app.desktop, port, app.running).open()
    try:
        serving.join()
    except KeyboardInterrupt:
        pass
    finally:
        close(server, app.running)


def close(server: "PageServer", keys: PrivateFolder) -> None:
    keys.forget(page_key_name(server.server_address[1]))
    server.shutdown()
    server.server_close()


def serve_in_background(app, port: int, owner_check: OwnerCheck = owned_by_this_user, keys: PrivateFolder | None = None) -> "PageServer | None":
    server = _bind(app, port, owner_check, keys or app.running)
    if server is not None:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class PageServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address) -> None:
        print(f"chronata page: a request failed: {sys.exc_info()[1]!r}", file=sys.stderr)


def _bind(app, port: int, owner_check: OwnerCheck, keys: PrivateFolder) -> "PageServer | None":
    key = secrets.token_urlsafe(32)
    try:
        server = PageServer((HOST, port), _handler(app, port, key, Visits(), owner_check))
    except OSError:
        return None
    try:
        keys.write(page_key_name(port), key)
    except Exception:
        server.server_close()
        raise
    return server


def _page(pages: Path, visit: Visit) -> bytes:
    return (pages / "index.html").read_text(encoding="utf-8").replace("{{token}}", visit.form_token).encode("utf-8")


def _page_file(pages: Path, path: str) -> tuple[str, bytes] | None:
    if not PAGE_FILE.match(path) or not (pages / path.lstrip("/")).is_file():
        return None
    return f"{CONTENT_TYPES[path.rsplit('.', 1)[1]]}; charset=utf-8", (pages / path.lstrip("/")).read_bytes()


def _size(given: str) -> int:
    return int(given) if given.isdigit() else -1


def _handler(app, port: int, key: str, visits: Visits, owner_check: OwnerCheck) -> type[BaseHTTPRequestHandler]:
    allowed_hosts = {f"{HOST}:{port}", f"localhost:{port}"}
    allowed_origins = {f"http://{host}" for host in allowed_hosts}
    cookie_name = f"chronata_{port}"
    reads, dialogs, changes = requests.reads(app), requests.dialogs(app), requests.changes(app)

    class Handler(BaseHTTPRequestHandler):
        timeout = IDLE_SECONDS

        def handle(self):
            if owner_check(self.client_address, self.server.server_address):
                super().handle()

        def do_GET(self):
            if not self._addressed_to_this_page():
                return self._send(403, "text/plain", b"forbidden")
            address = urlparse(self.path)
            if address.path == DOOR_PATH:
                return self._enter(dict(parse_qsl(address.query)).get("code", ""))
            visit = self._visit()
            if visit is None:
                return self._locked(address.path)
            if address.path == "/":
                return self._send(200, HTML, _page(app.web_page, visit))
            page_file = _page_file(app.web_page, address.path)
            if page_file:
                return self._send(200, *page_file)
            if not self._carries_form_token(visit):
                return self._json(403, {"error": "forbidden"})
            if address.path not in reads:
                return self._json(404, {"error": "not found"})
            self._answer(lambda: self._json(200, reads[address.path](dict(parse_qsl(address.query)))))

        def do_POST(self):
            if not self._addressed_to_this_page():
                return self._json(403, {"error": "forbidden"})
            if self.path == LAUNCH_CODE_PATH:
                return self._hand_out_launch_code()
            visit = self._visit()
            if visit is None:
                return self._json(401, {"error": OPEN_AGAIN})
            if not self._carries_form_token(visit) or not self._sent_by_the_page():
                return self._json(403, {"error": "forbidden"})
            if self.path not in dialogs and self.path not in changes:
                return self._json(404, {"error": "not found"})
            size = _size(self.headers.get("Content-Length", "0"))
            if not 0 <= size <= LARGEST_REQUEST:
                return self._json(413, {"error": "that request is too large"})
            self._answer(lambda: self._changed(json.loads(self.rfile.read(size) or b"{}")))

        def _changed(self, body: dict) -> None:
            if self.path in dialogs:
                return self._json(200, dialogs[self.path](body))
            outcome = changes[self.path](body)
            self._json(200, {"message": outcome.message, "warning": outcome.warning})

        def _answer(self, reply: Callable[[], None]) -> None:
            try:
                reply()
            except Exception as error:
                refused = refusal(error)
                if refused is None:
                    print(f"chronata page: {self.path} failed: {error!r}", file=sys.stderr)
                    return self._json(500, {"error": "Chronata could not do that; the details are in its log"})
                self._json(*refused)

        def _addressed_to_this_page(self) -> bool:
            return self.headers.get("Host") in allowed_hosts

        def _hand_out_launch_code(self) -> None:
            nonce = self.headers.get("X-Door-Nonce", "")
            if "Origin" in self.headers or len(nonce) < 32 or not proves(key, self.headers.get("X-Door-Proof", ""), ASKED_BY_THE_DOOR, nonce):
                return self._json(403, {"error": "forbidden"})
            code = visits.launch_code()
            self._json(200, {"code": code, "proof": proof(key, ANSWERED_BY_THE_PAGE, nonce, code)})

        def _enter(self, code: str) -> None:
            visit = visits.enter(code)
            if visit is None:
                return self._locked("/")
            self._send(303, "text/plain", b"", {"Location": "/", "Set-Cookie": f"{cookie_name}={visit.id}; HttpOnly; SameSite=Strict; Path=/"})

        def _visit(self) -> Visit | None:
            try:
                sent = SimpleCookie(self.headers.get("Cookie", "")).get(cookie_name)
            except CookieError:
                return None
            return visits.find(sent.value) if sent else None

        def _carries_form_token(self, visit: Visit) -> bool:
            return secrets.compare_digest(self.headers.get("X-Token", ""), visit.form_token)

        def _sent_by_the_page(self) -> bool:
            return self.headers.get("Origin") in allowed_origins and self.headers.get("Sec-Fetch-Site", "same-origin") == "same-origin"

        def _locked(self, path: str) -> None:
            if path == "/":
                return self._send(401, HTML, (app.web_page / "locked.html").read_bytes())
            self._json(401, {"error": OPEN_AGAIN})

        def _json(self, status: int, payload: dict) -> None:
            self._send(status, "application/json", json.dumps(payload).encode("utf-8"))

        def _send(self, status: int, content_type: str, body: bytes, extra_headers: dict[str, str] | None = None) -> None:
            self.send_response(status)
            for name, value in {"Content-Type": content_type, "Content-Length": str(len(body)), **SAFETY_HEADERS, **(extra_headers or {})}.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    return Handler
