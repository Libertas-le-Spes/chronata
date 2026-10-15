import webbrowser
from typing import Callable

from chronata.adapters.desktop import tk_dialogs

APP_ID = "Chronata.Chronata"
APP_NAME = "Chronata"


class WindowsDesktop:
    def __init__(self):
        self._toaster = None

    def notify(self, summary: str, body: str = "", on_click: Callable[[], None] | None = None, click_label: str = "Open") -> None:
        toaster = self._ready_toaster()
        if toaster is None:
            return
        from windows_toasts import Toast, ToastButton
        toast = Toast([summary, body] if body else [summary])
        if on_click is not None:
            toast.AddAction(ToastButton(click_label, "default"))
            toast.on_activated = lambda event: on_click() if event.arguments in ("default", "") else None
        toaster.show_toast(toast)

    def open_page(self, url: str) -> None:
        webbrowser.open(url)

    def choose_folder(self) -> str | None:
        return tk_dialogs.pick_folder("Where should Chronata save?")

    def ask(self, question: str, suggested: str) -> str | None:
        return tk_dialogs.ask(APP_NAME, question, suggested)

    def choose(self, question: str, options: list[str]) -> str | None:
        return tk_dialogs.choose(APP_NAME, question, options)

    def _ready_toaster(self):
        if self._toaster is None:
            try:
                from windows_toasts import InteractableWindowsToaster
            except ImportError:
                return None
            _register_app_id()
            self._toaster = InteractableWindowsToaster(APP_NAME, notifierAUMID=APP_ID)
        return self._toaster


def _register_app_id() -> None:
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\AppUserModelId\{APP_ID}") as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
