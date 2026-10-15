import argparse
import sys
import threading

from chronata.entrypoints.web.server import DEFAULT_PORT, page_url, serve_in_background
from chronata.use_cases.reminders import Reminders


def run(app, port: int, with_tray: bool = True) -> None:
    if not serve_in_background(app, port):
        print(f"port {port} is taken; the page is served by whatever holds it", file=sys.stderr)
    reminders = Reminders(app.sheet, app.desktop, page_url(port))
    tray = _tray(app, page_url(port)) if with_tray else None
    if tray is None:
        reminders.run_forever()
        return
    threading.Thread(target=reminders.run_forever, daemon=True).start()
    tray.run()


def main() -> None:
    from chronata.wiring import open_app
    arguments = argparse.ArgumentParser(prog="chronata-background")
    arguments.add_argument("--port", type=int, default=DEFAULT_PORT)
    arguments.add_argument("--no-tray", action="store_true")
    chosen = arguments.parse_args()
    run(open_app(), chosen.port, with_tray=not chosen.no_tray)


def _tray(app, url: str):
    try:
        from chronata.entrypoints.tray.tray_icon import TrayIcon
    except ImportError:
        return None
    return TrayIcon(app, url)
