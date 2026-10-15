import shutil
import subprocess
import threading
import webbrowser
from typing import Callable

from chronata.adapters.desktop import tk_dialogs

APP_NAME = "Chronata"
FOLDER_TITLE = "Where should Chronata save?"
FOLDER_PICKERS = [
    ["zenity", "--file-selection", "--directory", f"--title={FOLDER_TITLE}"],
    ["kdialog", "--getexistingdirectory", "--title", FOLDER_TITLE],
]


class LinuxDesktop:
    def notify(self, summary: str, body: str = "", on_click: Callable[[], None] | None = None, click_label: str = "Open") -> None:
        if shutil.which("notify-send") is None:
            return
        command = ["notify-send", "-a", APP_NAME, summary, body]
        if on_click is None:
            subprocess.run(command, check=False)
            return

        def wait_for_click():
            answered = subprocess.run([*command, f"--action=default={click_label}"], capture_output=True, text=True, check=False)
            if answered.stdout.strip() == "default":
                on_click()

        threading.Thread(target=wait_for_click, daemon=True).start()

    def open_page(self, url: str) -> None:
        webbrowser.open(url)

    def choose_folder(self) -> str | None:
        for picker in FOLDER_PICKERS:
            if shutil.which(picker[0]):
                try:
                    chosen = subprocess.run(picker, capture_output=True, text=True, check=False, timeout=600)
                except subprocess.TimeoutExpired:
                    return None
                return chosen.stdout.strip() or None
        return tk_dialogs.pick_folder(FOLDER_TITLE)

    def ask(self, question: str, suggested: str) -> str | None:
        if shutil.which("zenity") is None:
            return tk_dialogs.ask(APP_NAME, question, suggested)
        answered = _zenity("--entry", f"--title={APP_NAME}", f"--text={question}", f"--entry-text={suggested}")
        return answered.stdout.strip() if answered and answered.returncode == 0 else None

    def choose(self, question: str, options: list[str]) -> str | None:
        if shutil.which("zenity") is None:
            return tk_dialogs.choose(APP_NAME, question, options)
        buttons = [f"--extra-button={option}" for option in [*options, tk_dialogs.CANCEL]]
        answered = _zenity("--question", "--switch", "--no-markup", f"--title={APP_NAME}", f"--text={question}", *buttons)
        picked = answered.stdout.strip() if answered else ""
        return picked if picked and picked != tk_dialogs.CANCEL else None


def _zenity(*arguments: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["zenity", *arguments], capture_output=True, text=True, check=False, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return None
