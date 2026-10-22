import hashlib
import os
from pathlib import Path


def log_folder() -> Path:
    if "CHRONATA_HOME" in os.environ:
        return Path(os.environ["CHRONATA_HOME"])
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "chronata"


def settings_folder() -> Path:
    if "CHRONATA_CONFIG" in os.environ:
        return Path(os.environ["CHRONATA_CONFIG"])
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "chronata"


def repository_copies_folder(log: Path) -> Path:
    return log.parent / "chronata-places"


def runtime_folder() -> Path:
    running = os.environ.get("XDG_RUNTIME_DIR")
    if running:
        return Path(running) / "chronata"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "chronata" / "running"


def lock_name(log: Path) -> str:
    return f"log-{hashlib.sha256(str(log.resolve()).encode()).hexdigest()[:16]}.lock"


def web_page_folder() -> Path:
    return Path(__file__).resolve().parents[4] / "frontend" / "web"
