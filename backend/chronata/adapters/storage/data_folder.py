from pathlib import Path

from chronata.adapters.storage.changed_files import WRITTEN_LIST, NamesInFile, write_changed
from chronata.adapters.storage.owner_only_file import make_owner_only_folder
from chronata.adapters.storage.place_folder import PlaceFolder

LEDGER = "ledger.jsonl"
RULES = "rules.json"
TIMESTAMPS = "timestamps"


class DataFolder:
    def __init__(self, directory: Path):
        make_owner_only_folder(directory)
        self.directory = directory
        self.ledger = directory / LEDGER
        self.rules = directory / RULES
        self.timestamps = directory / TIMESTAMPS

    def keep_readable(self, files: dict[str, bytes]) -> None:
        write_changed(PlaceFolder(self.directory), files, NamesInFile(self.directory / WRITTEN_LIST))

    def sealed_files(self) -> dict[str, bytes]:
        files = {f"sealed/{path.name}": path.read_bytes() for path in (self.ledger, self.rules) if path.exists()}
        for receipt in sorted(self.timestamps.glob("*.tsr")):
            files[f"sealed/{TIMESTAMPS}/{receipt.name}"] = receipt.read_bytes()
        return files


def find_saved_copy(folder: Path) -> Path:
    for candidate in (folder, folder / "sealed", folder / "Chronata" / "sealed"):
        if (candidate / LEDGER).exists():
            return candidate
    raise FileNotFoundError(f"no Chronata log found in {folder}")
