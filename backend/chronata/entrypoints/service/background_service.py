import signal
import sys

from chronata.entrypoints.web.page_door import PageDoor
from chronata.entrypoints.web.server import close, serve_in_background
from chronata.use_cases.reminders.reminders import Reminders


def run(app, port: int) -> None:
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    server = serve_in_background(app, port)
    if server is None:
        print(f"port {port} is taken by another program, so the page is not served; the door will not open it", file=sys.stderr)
    try:
        Reminders(app.log, app.clocking, app.pc, app.desktop, PageDoor(app.desktop, port, app.running)).run_forever()
    finally:
        if server is not None:
            close(server, app.running)
