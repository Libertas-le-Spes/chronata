import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from chronata.entrypoints.web.page_state import page_state
from chronata.timekeeping.record import TamperedRecord
from chronata.use_cases.outcome import UserError
from chronata.use_cases.verification import verify

PAGES = Path(__file__).parent / "page"
DEFAULT_PORT = 47630
STATIC = {"/app.js": "text/javascript", "/style.css": "text/css"}


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


def _actions(app) -> dict:
    sheet, saving = app.sheet, app.saving
    return {
        "/api/in": lambda body: sheet.clock_in(body.get("at"), body.get("note"), body.get("label", "")),
        "/api/out": lambda body: sheet.clock_out(body.get("at"), body.get("note")),
        "/api/add": lambda body: sheet.add(body.get("date"), body.get("start"), body.get("end"), body.get("reason"), body.get("note"), body.get("label", "")),
        "/api/label": lambda body: sheet.label(int(body["id"]), body.get("label", "")),
        "/api/correct": lambda body: sheet.correct(int(body["id"]), body.get("start"), body.get("end"), body.get("reason")),
        "/api/strike": lambda body: sheet.strike(int(body["id"]), body.get("reason")),
        "/api/explain": lambda body: sheet.explain_break(int(body["id"]), body.get("start", ""), body.get("reason")),
        "/api/paid": lambda body: sheet.record_payment(
            body.get("from"), body.get("to"), float(body.get("hours", "")), bool(body.get("timeOff")), body.get("reference")
        ),
        "/api/save": lambda body: sheet.save_now(),
        "/api/places/add": lambda body: saving.add_place(sheet, body.get("kind", ""), body.get("name", ""), body.get("target", ""),
                                                         body.get("username", ""), body.get("password", "")),
        "/api/places/remove": lambda body: saving.remove_place(body.get("id", "")),
        "/api/setup": lambda body: sheet.configure(body.get("lunch", ""), body.get("shift", "")),
    }


def _bind(app, port: int) -> HTTPServer | None:
    try:
        return HTTPServer(("127.0.0.1", port), _handler(app, port, secrets.token_urlsafe(32)))
    except OSError:
        return None


def _handler(app, port: int, token: str) -> type[BaseHTTPRequestHandler]:
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    routes = _actions(app)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get("Host") not in allowed_hosts:
                return self._send(403, "text/plain", b"forbidden")
            if self.path == "/":
                page = (PAGES / "index.html").read_text(encoding="utf-8").replace("{{token}}", token)
                return self._send(200, "text/html; charset=utf-8", page.encode("utf-8"))
            if self.path in STATIC:
                return self._send(200, f"{STATIC[self.path]}; charset=utf-8", (PAGES / self.path.lstrip("/")).read_bytes())
            if not self._trusted():
                return self._json(403, {"error": "forbidden"})
            if self.path == "/api/state":
                return self._json(200, page_state(app))
            if self.path == "/api/verify":
                return self._json(200, {"problems": verify(app.sheet.record, app.timestamper, app.history).problems})
            return self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._trusted():
                return self._json(403, {"error": "forbidden"})
            if self.path == "/api/choose-folder":
                return self._json(200, {"path": app.desktop.choose_folder()})
            action = routes.get(self.path)
            if action is None:
                return self._json(404, {"error": "not found"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                outcome = action(body)
            except (UserError, TamperedRecord) as error:
                return self._json(400, {"error": str(error)})
            except (KeyError, ValueError):
                return self._json(400, {"error": "some fields are missing or not numbers"})
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
