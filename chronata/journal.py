import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Boot:
    id: str
    on: datetime
    last_seen: datetime
    current: bool


def current_boot_id() -> str:
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip().replace("-", "")


def boots() -> list[Boot]:
    listed = subprocess.run(["journalctl", "--list-boots", "-o", "json", "--no-pager"], capture_output=True, text=True, check=False)
    if listed.returncode != 0 or not listed.stdout.strip():
        return []
    current = current_boot_id()
    return [
        Boot(boot["boot_id"], _moment(boot["first_entry"]), _moment(boot["last_entry"]), boot["boot_id"] == current)
        for boot in json.loads(listed.stdout)
    ]


def _moment(microseconds: int) -> datetime:
    return datetime.fromtimestamp(microseconds / 1_000_000).astimezone().replace(microsecond=0)
