import sys

from chronata.entrypoints.web.server import page_url, serve_in_background
from chronata.use_cases.reminders import Reminders


def run(app, port: int) -> None:
    if not serve_in_background(app, port):
        print(f"port {port} is taken; the page is served by whatever holds it", file=sys.stderr)
    Reminders(app.log, app.clocking, app.pc, app.desktop, page_url(port)).run_forever()
