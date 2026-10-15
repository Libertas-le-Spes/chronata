import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from chronata.timekeeping.pc.pc_sessions import Boot

ISO = r"\d{4}-\d{2}-\d{2}T[\d:]+[+-]\d{2}:?\d{2}"
REBOOT_LINE = re.compile(rf"^reboot\s.*?({ISO})(?:\s+-\s+(?:({ISO})|\S+))?(?:\s+\((?:(\d+)\+)?(\d+):(\d+)\))?")


class LastLog:
    def current_boot_id(self) -> str:
        return _boot_id(_current_boot_time())

    def boots(self) -> list[Boot]:
        listed = subprocess.run(["last", "-x", "--time-format", "iso", "reboot"], capture_output=True, text=True, check=False)
        starts = boots_from_last(listed.stdout) if listed.returncode == 0 else []
        current = _current_boot_time()
        found = [Boot(_boot_id(on), on, off or on, False) for on, off in starts if abs((on - current).total_seconds()) > 120]
        return sorted([*found, Boot(_boot_id(current), current, datetime.now().astimezone().replace(microsecond=0), True)], key=lambda b: b.on)

    def shutting_down(self) -> bool:
        return False


def boots_from_last(output: str) -> list[tuple[datetime, datetime | None]]:
    found = []
    for line in output.splitlines():
        match = REBOOT_LINE.match(line)
        if not match:
            continue
        on = datetime.fromisoformat(match.group(1))
        if match.group(2):
            found.append((on, datetime.fromisoformat(match.group(2))))
        elif match.group(4):
            found.append((on, on + timedelta(days=int(match.group(3) or 0), hours=int(match.group(4)), minutes=int(match.group(5)))))
        else:
            found.append((on, None))
    return found


def _current_boot_time() -> datetime:
    for line in Path("/proc/stat").read_text().splitlines():
        if line.startswith("btime "):
            return datetime.fromtimestamp(int(line.split()[1])).astimezone()
    return datetime.now().astimezone().replace(microsecond=0)


def _boot_id(on: datetime) -> str:
    return f"boot-{on:%Y%m%dT%H%M%S}"
