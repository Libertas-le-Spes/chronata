import html
import shutil
import subprocess
import threading
import webbrowser
from typing import Callable

from chronata.adapters.desktop.kdialog import KDialog
from chronata.adapters.desktop.zenity import Zenity

APP_NAME = "Chronata"
FOLDER_TITLE = "Where should Chronata save?"
DIALOG_TOOLS = {"zenity": Zenity, "kdialog": KDialog}


class LinuxDesktop:
    def __init__(self):
        self.dialogs = _installed_dialogs()

    def notify(self, summary: str, body: str = "", on_click: Callable[[], None] | None = None, click_label: str = "Open") -> None:
        if shutil.which("notify-send") is None:
            return
        shown = ["--", summary, html.escape(body, quote=False)]
        if on_click is None:
            subprocess.run(["notify-send", "-a", APP_NAME, *shown], check=False)
            return

        def wait_for_click():
            question = ["notify-send", "-a", APP_NAME, "--urgency=critical", f"--action=default={click_label}", *shown]
            answered = subprocess.run(question, capture_output=True, text=True, check=False)
            if answered.stdout.strip() == "default":
                on_click()

        threading.Thread(target=wait_for_click, daemon=True).start()

    def open_page(self, url: str) -> None:
        webbrowser.open(url)

    def can_ask(self) -> bool:
        return self.dialogs is not None

    def choose_folder(self) -> str | None:
        return self.dialogs.pick_folder(FOLDER_TITLE) if self.dialogs else None

    def ask(self, question: str, suggested: str) -> str | None:
        return self.dialogs.ask(APP_NAME, question, suggested) if self.dialogs else None

    def choose(self, question: str, options: list[str]) -> str | None:
        return self.dialogs.choose(APP_NAME, question, options) if self.dialogs else None


def _installed_dialogs():
    return next((tool() for name, tool in DIALOG_TOOLS.items() if shutil.which(name)), None)
