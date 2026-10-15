import subprocess
import threading
import webbrowser
from typing import Callable

APP_NAME = "Chronata"
CANCEL = "Cancel"


class LinuxDesktop:
    def notify(self, summary: str, body: str = "", on_click: Callable[[], None] | None = None, click_label: str = "Open") -> None:
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
        chosen = _zenity("--file-selection", "--directory", "--title=Where should Chronata save?")
        return chosen.stdout.strip() or None if chosen else None

    def ask(self, question: str, suggested: str) -> str | None:
        answered = _zenity("--entry", f"--title={APP_NAME}", f"--text={question}", f"--entry-text={suggested}")
        return answered.stdout.strip() if answered and answered.returncode == 0 else None

    def choose(self, question: str, options: list[str]) -> str | None:
        buttons = [f"--extra-button={option}" for option in [*options, CANCEL]]
        answered = _zenity("--question", "--switch", "--no-markup", f"--title={APP_NAME}", f"--text={question}", *buttons)
        picked = answered.stdout.strip() if answered else ""
        return picked if picked and picked != CANCEL else None


def _zenity(*arguments: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["zenity", *arguments], capture_output=True, text=True, check=False, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return None
