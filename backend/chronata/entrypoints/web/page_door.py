import json
from http.client import HTTPConnection

from chronata.entrypoints.web.address import HOST, page_key_name, page_url
from chronata.use_cases.log.ports import Desktop, NotPrivate, PrivateFolder

LAUNCH_CODE_PATH = "/door/code"
DOOR_PATH = "/door"


class PageDoor:
    def __init__(self, desktop: Desktop, port: int, keys: PrivateFolder):
        self.desktop = desktop
        self.port = port
        self.keys = keys

    def open(self, section: str = "") -> None:
        try:
            code = self._launch_code()
        except NotPrivate as error:
            self.desktop.notify("Chronata will not open its page", str(error))
            return
        if code is None:
            self.desktop.notify("Chronata's page is not running", "Start it with: systemctl --user start chronata, or run: chronata ui")
            return
        self.desktop.open_page(f"{page_url(self.port).rstrip('/')}{DOOR_PATH}?code={code}" + (f"#{section}" if section else ""))

    def _launch_code(self) -> str | None:
        key = self.keys.read(page_key_name(self.port))
        if key is None:
            return None
        connection = HTTPConnection(HOST, self.port, timeout=5)
        try:
            connection.request("POST", LAUNCH_CODE_PATH, body=b"", headers={"X-Page-Key": key})
            reply = connection.getresponse()
            return json.loads(reply.read()).get("code") if reply.status == 200 else None
        except (OSError, ValueError):
            return None
        finally:
            connection.close()
