import sys

from chronata.entrypoints.web.page_door import PageDoor
from chronata.entrypoints.web.server import serve_in_background
from chronata.use_cases.reminders.reminders import Reminders


def run(app, port: int) -> None:
    if serve_in_background(app, port) is None:
        print(f"port {port} is taken; the page is served by whatever holds it", file=sys.stderr)
    Reminders(app.log, app.clocking, app.pc, app.desktop, PageDoor(app.desktop, port, app.running)).run_forever()
