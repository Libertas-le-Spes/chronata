import os
from pathlib import Path

from chronata.use_cases.ports import SaveError

WRITTEN_LIST = ".chronata-files"


def write_changed(folder: Path, bundle: dict[str, bytes]) -> None:
    try:
        for relative, content in bundle.items():
            path = folder / relative
            if path.exists() and path.read_bytes() == content:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.name}.chronata-tmp")
            temporary.write_bytes(content)
            os.replace(temporary, path)
        _remove_no_longer_written(folder, set(bundle))
    except OSError as error:
        raise SaveError(f"could not write to {folder}: {error.strerror or error}")


def _remove_no_longer_written(folder: Path, written: set[str]) -> None:
    listing = folder / WRITTEN_LIST
    before = set(listing.read_text(encoding="utf-8").splitlines()) if listing.exists() else set()
    for relative in sorted(before - written):
        _remove(folder / relative, folder)
    listing.write_text("\n".join(sorted(written)) + "\n", encoding="utf-8")


def _remove(stale: Path, folder: Path) -> None:
    if stale.is_file():
        stale.unlink()
    for parent in stale.parents:
        if not _empty_below(parent, folder):
            break
        parent.rmdir()


def _empty_below(parent: Path, folder: Path) -> bool:
    if parent == folder or not parent.is_dir():
        return False
    return not any(parent.iterdir())
