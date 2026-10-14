import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from chronata.ledger import TamperedLedger
from chronata.desktop import choose_folder
from chronata.places import SaveError
from chronata.timesheet import Outcome, Timesheet, UserError
from chronata.web.state import state

PAGES = Path(__file__).parent / "page"
STATIC = {"/app.js": "text/javascript", "/style.css": "text/css"}


def actions(sheet: Timesheet) -> dict:
    return {
        "/api/in": lambda body: sheet.clock_in(body.get("at"), body.get("note"), body.get("label", "")),
        "/api/out": lambda body: sheet.clock_out(body.get("at"), body.get("note")),
        "/api/add": lambda body: sheet.add(body.get("date"), body.get("start"), body.get("end"), body.get("reason"), body.get("note"), body.get("label", "")),
        "/api/label": lambda body: sheet.label(int(body["id"]), body.get("label", "")),
        "/api/correct": lambda body: sheet.correct(int(body["id"]), body.get("start"), body.get("end"), body.get("reason")),
        "/api/strike": lambda body: sheet.strike(int(body["id"]), body.get("reason")),
        "/api/paid": lambda body: sheet.record_payment(
            body.get("from"), body.get("to"), float(body.get("hours", "")), bool(body.get("timeOff")), body.get("reference")
        ),
        "/api/save": lambda body: sheet.save_now(),
        "/api/places/add": lambda body: _add_place(sheet, body),
        "/api/places/remove": lambda body: _remove_place(sheet, body),
        "/api/setup": lambda body: sheet.configure(body.get("lunch", ""), body.get("shift", "")),
    }


def _add_place(sheet: Timesheet, body: dict) -> Outcome:
    place = sheet.publish.book.add(body.get("kind", ""), body.get("name", ""), body.get("target", ""),
                                   body.get("username", ""), body.get("password", ""))
    saved = sheet.save_now()
    return Outcome(f"added {place.name} and {saved.message}", saved.warning)


def _remove_place(sheet: Timesheet, body: dict) -> Outcome:
    place = sheet.publish.book.remove(body.get("id", ""))
    return Outcome(f"removed {place.name}; copies already saved there are left as they are", None)


def page_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/"


def bind(sheet: Timesheet, port: int) -> HTTPServer | None:
    try:
        return HTTPServer(("127.0.0.1", port), _handler(sheet, port, secrets.token_urlsafe(32)))
    except OSError:
        return None


def serve(sheet: Timesheet, port: int, open_browser: bool) -> None:
    server = bind(sheet, port)
    if server is None:
        print(f"already running at {page_url(port)}")
    else:
        print(f"chronata at {page_url(port)} (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(page_url(port))
    if server is None:
        return
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def serve_in_background(sheet: Timesheet, port: int) -> bool:
    server = bind(sheet, port)
    if server is None:
        return False
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return True


def _handler(sheet: Timesheet, port: int, token: str) -> type[BaseHTTPRequestHandler]:
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    routes = actions(sheet)

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
                return self._json(200, state(sheet))
            if self.path == "/api/verify":
                return self._json(200, {"problems": sheet.problems(include_history=True)})
            return self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._trusted():
                return self._json(403, {"error": "forbidden"})
            if self.path == "/api/choose-folder":
                return self._json(200, {"path": choose_folder()})
            action = routes.get(self.path)
            if action is None:
                return self._json(404, {"error": "not found"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                outcome = action(body)
            except (UserError, TamperedLedger, SaveError) as error:
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
