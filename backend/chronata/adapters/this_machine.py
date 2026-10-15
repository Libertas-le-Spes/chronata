from pathlib import Path

from chronata.adapters.desktop.linux_desktop import LinuxDesktop
from chronata.adapters.power.last_log import LastLog
from chronata.adapters.power.systemd_journal import SystemdJournal
from chronata.use_cases.log.ports import Desktop, PowerHistory

SYSTEMD_RUNNING = Path("/run/systemd/system")


def desktop() -> Desktop:
    return LinuxDesktop()


def power_history(systemd_running: Path = SYSTEMD_RUNNING) -> PowerHistory:
    return SystemdJournal() if systemd_running.is_dir() else LastLog()
