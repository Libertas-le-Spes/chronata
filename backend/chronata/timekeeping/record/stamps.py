from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Stamp:
    seq: int
    authority: str
    authority_name: str
    time: datetime
    name: str


def latest(stamps: list[Stamp]) -> tuple[int | None, list[Stamp]]:
    newest = max((s.seq for s in stamps), default=None)
    return newest, [s for s in stamps if s.seq == newest]
