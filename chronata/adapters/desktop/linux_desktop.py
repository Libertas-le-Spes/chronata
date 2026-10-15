import shutil
import subprocess
import threading
import webbrowser
from typing import Callable

from chronata.adapters.desktop.folder_picker import pick_with_tk

APP_NAME = "Chronata"
FOLDER_PICKERS = [
    ["zenity", "--file-selection", "--directory", "--title=Where should Chronata save?"],
    ["kdialog", "--getexistingdirectory", "--title", "Where should Chronata save?"],
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
        return pick_with_tk()
