import json
import os
from http.client import HTTPConnection
from typing import Callable

from chronata.entrypoints.web.address import HOST, page_key_name, page_url
from chronata.entrypoints.web.connection_owner import who_listens_on
from chronata.entrypoints.web.door_proof import ANSWERED_BY_THE_PAGE, ASKED_BY_THE_DOOR, fresh_nonce, proof, proves
from chronata.use_cases.log.ports import Desktop, NotPrivate, PrivateFolder

LAUNCH_CODE_PATH = "/door/code"
DOOR_PATH = "/door"
ANSWER_SECONDS = 5

ListenerOwner = Callable[[tuple[str, int]], int | None]


class PageDoor:
    def __init__(self, desktop: Desktop, port: int, keys: PrivateFolder, listener_owner: ListenerOwner = who_listens_on):
        self.desktop = desktop
        self.port = port
        self.keys = keys
        self.listener_owner = listener_owner

    def open(self, section: str = "") -> None:
        try:
            key = self.keys.read(page_key_name(self.port))
        except NotPrivate as error:
            self.desktop.notify("Chronata will not open its page", str(error))
            return
        owner = self.listener_owner((HOST, self.port))
        if key is None or owner is None:
            self.keys.forget(page_key_name(self.port))
            self.desktop.notify("Chronata's page is not running", "Start it with: systemctl --user start chronata, or run: chronata ui")
            return
        if owner != os.getuid():
            self.desktop.notify("Chronata will not open its page", f"Port {self.port} is held by a program that is not Chronata running as you.")
            return
        code = self._launch_code(key)
        if code is None:
            self.desktop.notify("Chronata will not open its page", f"The program on port {self.port} could not prove it is your Chronata.")
            return
        self.desktop.open_page(f"{page_url(self.port).rstrip('/')}{DOOR_PATH}?code={code}" + (f"#{section}" if section else ""))

    def _launch_code(self, key: str) -> str | None:
        nonce = fresh_nonce()
        connection = HTTPConnection(HOST, self.port, timeout=ANSWER_SECONDS)
        try:
            connection.request("POST", LAUNCH_CODE_PATH, body=b"", headers={"X-Door-Nonce": nonce, "X-Door-Proof": proof(key, ASKED_BY_THE_DOOR, nonce)})
            reply = connection.getresponse()
            answer = json.loads(reply.read(4096)) if reply.status == 200 else {}
        except (OSError, ValueError):
            return None
        finally:
            connection.close()
        code, answered = (answer.get("code"), answer.get("proof")) if isinstance(answer, dict) else (None, None)
        if not isinstance(code, str) or not isinstance(answered, str) or not proves(key, answered, ANSWERED_BY_THE_PAGE, nonce, code):
            return None
        return code
