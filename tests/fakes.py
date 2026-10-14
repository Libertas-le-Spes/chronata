import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from chronata.timekeeping.pc_sessions import Boot
from chronata.wiring import App, open_app

SAST = timezone(timedelta(hours=2))


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=SAST)


class FakePower:
    def __init__(self):
        self.boot_list: list[Boot] = []
        self.booted = "today"
        self.stopping = False

    def boots(self) -> list[Boot]:
        return self.boot_list

    def current_boot_id(self) -> str:
        return self.booted

    def shutting_down(self) -> bool:
        return self.stopping


class FakeDesktop:
    def __init__(self):
        self.notices: list[tuple[str, object]] = []
        self.opened: list[str] = []

    def notify(self, summary, body="", on_click=None, click_label="Open"):
        self.notices.append((summary, on_click))

    def open_page(self, url):
        self.opened.append(url)

    def choose_folder(self):
        return None

    def click(self, summary_start: str) -> None:
        next(action for summary, action in self.notices if summary.startswith(summary_start) and action)()


class NoTimestamps:
    def stamp(self, seq, record_hash):
        return [], []

    def stamps(self):
        return []

    def check(self, stamp, record_hash):
        return None


class Fixture:
    def __init__(self, now: str = "2026-10-14T08:00:00"):
        self.now = at(now)
        self.power = FakePower()
        self.desktop = FakeDesktop()
        self.app: App = open_app(Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp()), clock=lambda: self.now,
                                 power=self.power, timestamper=NoTimestamps(), desktop=self.desktop)
        self.sheet = self.app.sheet

    def at(self, text: str) -> None:
        self.now = at(text)
