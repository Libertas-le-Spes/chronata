import os
from pathlib import Path

LEDGER = "ledger.jsonl"
WORKING_DAY = "rules.json"
TIMESTAMPS = "timestamps"


def default_location() -> Path:
    return Path(os.environ.get("CHRONATA_HOME", Path.home() / ".local" / "share" / "chronata"))


class DataFolder:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.directory = directory
        self.ledger = directory / LEDGER
        self.working_day = directory / WORKING_DAY
        self.timestamps = directory / TIMESTAMPS
        self.lock = directory / ".git" / "chronata.lock"

    def sealed_files(self) -> dict[str, bytes]:
        files = {f"sealed/{path.name}": path.read_bytes() for path in (self.ledger, self.working_day) if path.exists()}
        for receipt in sorted(self.timestamps.glob("*.tsr")):
            files[f"sealed/{TIMESTAMPS}/{receipt.name}"] = receipt.read_bytes()
        return files


def find_saved_copy(folder: Path) -> Path:
    for candidate in (folder, folder / "sealed", folder / "Chronata" / "sealed"):
        if (candidate / LEDGER).exists():
            return candidate
    raise FileNotFoundError(f"no Chronata log found in {folder}")
