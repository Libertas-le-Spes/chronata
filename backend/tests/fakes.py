import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from chronata.timekeeping.pc.pc_sessions import Boot
from chronata.use_cases.questions.questions import Answers
from chronata.wiring import App, open_app

SAST = timezone(timedelta(hours=2))


def hours(shift_start: str, shift_end: str, lunch_start: str = "", lunch_minutes: str = "", **more) -> Answers:
    return Answers(shift_start=shift_start, shift_end=shift_end, lunch_start=lunch_start, lunch_minutes=lunch_minutes, **more)


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
        self.answers: list[str | None] = []
        self.dialogs_installed = True
        self.asked: list[tuple[str, object]] = []

    def notify(self, summary, body="", on_click=None, click_label="Open"):
        self.notices.append((summary, on_click))

    def open_page(self, url):
        self.opened.append(url)

    def choose_folder(self):
        return None

    def can_ask(self):
        return self.dialogs_installed

    def ask(self, question, suggested):
        self.asked.append((question, suggested))
        return self.answers.pop(0)

    def choose(self, question, options):
        self.asked.append((question, options))
        return self.answers.pop(0)

    def click(self, summary_start: str) -> None:
        next(action for summary, action in self.notices if summary.startswith(summary_start) and action)()


class FakePage:
    def __init__(self):
        self.opened: list[str] = []

    def open(self, section=""):
        self.opened.append(section)


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
        self.page = FakePage()
        self.data = Path(tempfile.mkdtemp())
        self.app: App = open_app(self.data, Path(tempfile.mkdtemp()), clock=lambda: self.now,
                                 power=self.power, timestamper=NoTimestamps(), desktop=self.desktop)

    def at(self, text: str) -> None:
        self.now = at(text)
