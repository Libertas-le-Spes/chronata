def pick_with_tk() -> str | None:
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        return None
    window = tkinter.Tk()
    window.withdraw()
    window.attributes("-topmost", True)
    try:
        return filedialog.askdirectory(title="Where should Chronata save?") or None
    finally:
        window.destroy()
