import json
import re
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

from chronata.entrypoints.web import requests
from chronata.entrypoints.web.refusals import refusal

DEFAULT_PORT = 47630
PAGE_FILE = re.compile(r"^/([a-z_]+/)?[a-z_]+\.(js|css)$")
CONTENT_TYPES = {"js": "text/javascript", "css": "text/css"}


def page_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/"


def serve(app, port: int, open_browser: bool) -> None:
    server = _bind(app, port)
    print(f"chronata at {page_url(port)} (Ctrl+C to stop)" if server else f"already running at {page_url(port)}")
    if open_browser:
        webbrowser.open(page_url(port))
    if server is None:
        return
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def serve_in_background(app, port: int) -> bool:
    server = _bind(app, port)
    if server is None:
        return False
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return True


def _page_file(pages: Path, path: str, token: str) -> tuple[str, bytes] | None:
    if path == "/":
        return "text/html; charset=utf-8", (pages / "index.html").read_text(encoding="utf-8").replace("{{token}}", token).encode("utf-8")
    if not PAGE_FILE.match(path) or not (pages / path.lstrip("/")).is_file():
        return None
    return f"{CONTENT_TYPES[path.rsplit('.', 1)[1]]}; charset=utf-8", (pages / path.lstrip("/")).read_bytes()


def _bind(app, port: int) -> HTTPServer | None:
    try:
        return HTTPServer(("127.0.0.1", port), _handler(app, port, secrets.token_urlsafe(32)))
    except OSError:
        return None


def _handler(app, port: int, token: str) -> type[BaseHTTPRequestHandler]:
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    reads, dialogs, changes = requests.reads(app), requests.dialogs(app), requests.changes(app)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get("Host") not in allowed_hosts:
                return self._send(403, "text/plain", b"forbidden")
            page_file = _page_file(app.web_page, self.path, token)
            if page_file:
                return self._send(200, *page_file)
            if not self._trusted():
                return self._json(403, {"error": "forbidden"})
            address = urlparse(self.path)
            if address.path in reads:
                return self._json(200, reads[address.path](dict(parse_qsl(address.query))))
            return self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._trusted():
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

        def _trusted(self) -> bool:
            return self.headers.get("Host") in allowed_hosts and secrets.compare_digest(self.headers.get("X-Token", ""), token)

        def _json(self, status: int, payload: dict) -> None:
            self._send(status, "application/json", json.dumps(payload).encode("utf-8"))

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    return Handler
