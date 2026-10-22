import json
import re
import secrets
import threading
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qsl, urlparse

from chronata.entrypoints.web import requests
from chronata.entrypoints.web.address import HOST, page_key_name, page_url
from chronata.entrypoints.web.connection_owner import owned_by_this_user
from chronata.entrypoints.web.owner_only_folder import OwnerOnlyFolder, runtime_folder
from chronata.entrypoints.web.page_door import DOOR_PATH, LAUNCH_CODE_PATH, PageDoor
from chronata.entrypoints.web.refusals import refusal
from chronata.entrypoints.web.visits import Visit, Visits

PAGE_FILE = re.compile(r"^/([a-z_]+/)?[a-z_]+\.(js|css)$")
CONTENT_TYPES = {"js": "text/javascript", "css": "text/css"}
HTML = "text/html; charset=utf-8"
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
    server = _bind(app, port, owned_by_this_user, OwnerOnlyFolder(runtime_folder()))
    print(f"chronata at {page_url(port)} (Ctrl+C to stop)" if server else f"already running at {page_url(port)}")
    if server is None:
        if open_browser:
            PageDoor(app.desktop, port).open()
        return
    serving = threading.Thread(target=server.serve_forever, daemon=True)
    serving.start()
    if open_browser:
        PageDoor(app.desktop, port).open()
    try:
        serving.join()
    except KeyboardInterrupt:
        pass


def serve_in_background(app, port: int, owner_check: OwnerCheck = owned_by_this_user, keys: OwnerOnlyFolder | None = None) -> HTTPServer | None:
    server = _bind(app, port, owner_check, keys or OwnerOnlyFolder(runtime_folder()))
    if server is not None:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _bind(app, port: int, owner_check: OwnerCheck, keys: OwnerOnlyFolder) -> HTTPServer | None:
    key = secrets.token_urlsafe(32)
    try:
        server = HTTPServer((HOST, port), _handler(app, port, key, Visits(), owner_check))
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


def _handler(app, port: int, key: str, visits: Visits, owner_check: OwnerCheck) -> type[BaseHTTPRequestHandler]:
    allowed_hosts = {f"{HOST}:{port}", f"localhost:{port}"}
    allowed_origins = {f"http://{host}" for host in allowed_hosts}
    cookie_name = f"chronata_{port}"
    reads, dialogs, changes = requests.reads(app), requests.dialogs(app), requests.changes(app)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if not self._from_this_user():
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
            if address.path in reads:
                return self._json(200, reads[address.path](dict(parse_qsl(address.query))))
            return self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._from_this_user():
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
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                if self.path in dialogs:
                    return self._json(200, dialogs[self.path](body))
                outcome = changes[self.path](body)
            except Exception as error:
                refused = refusal(error)
                if refused is None:
                    raise
                return self._json(*refused)
            return self._json(200, {"message": outcome.message, "warning": outcome.warning})

        def _from_this_user(self) -> bool:
            return self.headers.get("Host") in allowed_hosts and owner_check(self.client_address, self.server.server_address)

        def _hand_out_launch_code(self) -> None:
            if "Origin" in self.headers or not secrets.compare_digest(self.headers.get("X-Page-Key", ""), key):
                return self._json(403, {"error": "forbidden"})
            self._json(200, {"code": visits.launch_code()})

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
