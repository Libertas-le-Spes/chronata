from contextlib import contextmanager

CANCEL = "Cancel"


def pick_folder(title: str) -> str | None:
    with _hidden_window() as window:
        if window is None:
            return None
        from tkinter import filedialog
        return filedialog.askdirectory(title=title, parent=window) or None


def ask(title: str, question: str, suggested: str) -> str | None:
    with _hidden_window() as window:
        if window is None:
            return None
        from tkinter import simpledialog
        answered = simpledialog.askstring(title, question, initialvalue=suggested, parent=window)
        return answered.strip() if answered is not None else None


def choose(title: str, question: str, options: list[str]) -> str | None:
    with _hidden_window() as window:
        if window is None:
            return None
        import tkinter
        picked: list[str] = []
        dialog = tkinter.Toplevel(window)
        dialog.title(title)
        dialog.attributes("-topmost", True)
        tkinter.Label(dialog, text=question, wraplength=360, justify="left").pack(padx=16, pady=(16, 8))
        for option in [*options, CANCEL]:
            tkinter.Button(dialog, text=option, command=lambda chosen=option: (picked.append(chosen), dialog.destroy())).pack(fill="x", padx=16, pady=2)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        window.wait_window(dialog)
        return picked[0] if picked and picked[0] != CANCEL else None


@contextmanager
def _hidden_window():
    try:
        import tkinter
        window = tkinter.Tk()
    except (ImportError, RuntimeError):
        yield None
        return
    window.withdraw()
    window.attributes("-topmost", True)
    try:
        yield window
    finally:
        window.destroy()
