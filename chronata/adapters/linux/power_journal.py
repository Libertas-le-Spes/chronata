import json
import subprocess
from datetime import datetime
from pathlib import Path

from chronata.timekeeping.pc_sessions import Boot


class PowerJournal:
    def current_boot_id(self) -> str:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip().replace("-", "")

    def boots(self) -> list[Boot]:
        listed = subprocess.run(["journalctl", "--list-boots", "-o", "json", "--no-pager"], capture_output=True, text=True, check=False)
        if listed.returncode != 0 or not listed.stdout.strip():
            return []
        current = self.current_boot_id()
        return [
            Boot(boot["boot_id"], _moment(boot["first_entry"]), _moment(boot["last_entry"]), boot["boot_id"] == current)
            for boot in json.loads(listed.stdout)
        ]

    def shutting_down(self) -> bool:
        state = subprocess.run(["systemctl", "is-system-running"], capture_output=True, text=True, check=False)
        return state.stdout.strip() == "stopping"


def _moment(microseconds: int) -> datetime:
    return datetime.fromtimestamp(microseconds / 1_000_000).astimezone().replace(microsecond=0)
