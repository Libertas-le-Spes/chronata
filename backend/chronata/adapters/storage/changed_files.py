from pathlib import Path
from typing import Protocol

from chronata.adapters.storage.owner_only_file import write_owner_only
from chronata.adapters.storage.place_folder import PlaceFolder
from chronata.use_cases.log.ports import SaveError

WRITTEN_LIST = ".chronata-files"


class WrittenNames(Protocol):
    def names(self) -> set[str]: ...
    def remember(self, names: set[str]) -> None: ...


class NamesInFile:
    def __init__(self, path: Path):
        self.path = path

    def names(self) -> set[str]:
        return set(self.path.read_text(encoding="utf-8").splitlines()) - {""} if self.path.exists() else set()

    def remember(self, names: set[str]) -> None:
        write_owner_only(self.path, listing(names))


def listing(names: set[str]) -> bytes:
    return ("\n".join(sorted(names)) + "\n").encode("utf-8")


def write_changed(folder: PlaceFolder, bundle: dict[str, bytes], written: WrittenNames) -> None:
    try:
        for relative, content in bundle.items():
            if not folder.holds(relative, content):
                folder.write(relative, content)
        for relative in sorted(written.names() - set(bundle)):
            folder.remove(relative)
        written.remember(set(bundle))
    except OSError as error:
        raise SaveError(f"could not write to {folder}: {error.strerror or error}")
