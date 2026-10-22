import secrets
import threading
import time
from dataclasses import dataclass
from typing import Callable

LAUNCH_CODE_SECONDS = 60
VISIT_SECONDS = 12 * 60 * 60


@dataclass(frozen=True)
class Visit:
    id: str
    form_token: str
    ends: float


class Visits:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self.launch_codes: dict[str, float] = {}
        self.open: dict[str, Visit] = {}
        self.one_at_a_time = threading.Lock()

    def launch_code(self) -> str:
        with self.one_at_a_time:
            self._forget_ended()
            code = secrets.token_urlsafe(32)
            self.launch_codes[code] = self.clock() + LAUNCH_CODE_SECONDS
            return code

    def enter(self, code: str) -> Visit | None:
        with self.one_at_a_time:
            self._forget_ended()
            if self.launch_codes.pop(code, None) is None:
                return None
            visit = Visit(secrets.token_urlsafe(32), secrets.token_urlsafe(32), self.clock() + VISIT_SECONDS)
            self.open[visit.id] = visit
            return visit

    def find(self, visit_id: str) -> Visit | None:
        with self.one_at_a_time:
            self._forget_ended()
            return self.open.get(visit_id)

    def _forget_ended(self) -> None:
        now = self.clock()
        self.launch_codes = {code: ends for code, ends in self.launch_codes.items() if ends > now}
        self.open = {visit_id: visit for visit_id, visit in self.open.items() if visit.ends > now}
