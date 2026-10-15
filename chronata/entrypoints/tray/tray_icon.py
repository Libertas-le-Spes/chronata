import threading

import pystray
from PIL import Image, ImageDraw

from chronata.entrypoints import clock_button

COLOURS = {"out": "#e5484d", "in": "#3e7bfa", "interrupted": "#f5a524"}
REFRESH_SECONDS = 10


def picture(state: str) -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    drawing = ImageDraw.Draw(image)
    drawing.ellipse((4, 4, 60, 60), fill=COLOURS.get(state, COLOURS["out"]))
    drawing.line((32, 32, 32, 14), fill="white", width=5)
    drawing.line((32, 32, 45, 39), fill="white", width=5)
    return image


class TrayIcon:
    def __init__(self, app, page_url: str):
        self.app = app
        self.page_url = page_url
        self.icon: pystray.Icon | None = None
        self.stopped = threading.Event()

    def run(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem(lambda item: self._toggle_wording(), self._toggle, default=True),
            pystray.MenuItem("Open Chronata", lambda: self.app.desktop.open_page(self.page_url)),
            pystray.MenuItem("Quit", self._quit),
        )
        self.icon = pystray.Icon("chronata", picture("out"), "Chronata", menu)
        self.icon.run(setup=self._start)

    def _start(self, icon: pystray.Icon) -> None:
        icon.visible = True
        self._refresh()
        threading.Thread(target=self._refresh_forever, daemon=True).start()

    def _toggle(self) -> None:
        clock_button.toggle(self.app)
        self._refresh()

    def _toggle_wording(self) -> str:
        return "Clock out" if clock_button.status(self.app)["state"] == "in" else "Clock in"

    def _refresh(self) -> None:
        status = clock_button.status(self.app)
        self.icon.icon = picture(status["state"])
        self.icon.title = status["tooltip"].replace("\n", " · ")[:120]

    def _refresh_forever(self) -> None:
        while not self.stopped.wait(REFRESH_SECONDS):
            self._refresh()

    def _quit(self) -> None:
        self.stopped.set()
        self.icon.stop()
