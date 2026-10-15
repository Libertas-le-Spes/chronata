import sys
from pathlib import Path

from chronata.adapters.desktop.linux_desktop import LinuxDesktop
from chronata.adapters.desktop.windows_desktop import WindowsDesktop
from chronata.adapters.power_history.last_log import LastLog
from chronata.adapters.power_history.systemd_journal import SystemdJournal
from chronata.adapters.power_history.windows_events import WindowsEvents
from chronata.use_cases.ports import Desktop, PowerHistory

SYSTEMD_RUNNING = Path("/run/systemd/system")


def desktop(platform: str = sys.platform) -> Desktop:
    return WindowsDesktop() if platform == "win32" else LinuxDesktop()


def power_history(platform: str = sys.platform, systemd_running: Path = SYSTEMD_RUNNING) -> PowerHistory:
    if platform == "win32":
        return WindowsEvents()
    return SystemdJournal() if systemd_running.is_dir() else LastLog()
