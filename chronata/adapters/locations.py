import hashlib
import os
import sys
import tempfile
from pathlib import Path


def log_folder() -> Path:
    if "CHRONATA_HOME" in os.environ:
        return Path(os.environ["CHRONATA_HOME"])
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Chronata" / "log"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "chronata"


def settings_folder() -> Path:
    if "CHRONATA_CONFIG" in os.environ:
        return Path(os.environ["CHRONATA_CONFIG"])
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Chronata"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "chronata"


def repository_copies_folder(log: Path) -> Path:
    return log.parent / "chronata-places"


def lock_file(log: Path) -> Path:
    guarded = hashlib.sha256(str(log.resolve()).encode()).hexdigest()[:16]
    running = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return Path(running) / f"chronata-{guarded}.lock"
