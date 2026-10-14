import subprocess
import threading
import webbrowser
from typing import Callable

APP_NAME = "Chronata"


def notify(summary: str, body: str = "", on_click: Callable[[], None] | None = None, click_label: str = "Open") -> None:
    command = ["notify-send", "-a", APP_NAME, summary, body]
    if on_click is None:
        subprocess.run(command, check=False)
        return

    def wait_for_click():
        answered = subprocess.run([*command, f"--action=default={click_label}"], capture_output=True, text=True, check=False)
        if answered.stdout.strip() == "default":
            on_click()

    threading.Thread(target=wait_for_click, daemon=True).start()


def choose_folder() -> str | None:
    try:
        chosen = subprocess.run(["zenity", "--file-selection", "--directory", "--title=Where should Chronata save?"],
                                capture_output=True, text=True, check=False, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return chosen.stdout.strip() or None


def open_page(url: str) -> None:
    webbrowser.open(url)
