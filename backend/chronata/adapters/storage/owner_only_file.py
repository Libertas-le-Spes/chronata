import os
import secrets
from pathlib import Path

OWNER_ONLY = 0o600
OWNER_ONLY_FOLDER = 0o700


def write_owner_only(path: Path, content: bytes) -> None:
    path.parent.mkdir(mode=OWNER_ONLY_FOLDER, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, OWNER_ONLY)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    _sync_folder(path.parent)


def append_owner_only(path: Path, content: bytes) -> None:
    path.parent.mkdir(mode=OWNER_ONLY_FOLDER, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, OWNER_ONLY)
    with os.fdopen(descriptor, "ab") as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())
    _sync_folder(path.parent)


def make_owner_only_folder(folder: Path) -> None:
    folder.mkdir(mode=OWNER_ONLY_FOLDER, parents=True, exist_ok=True)
    found = os.lstat(folder)
    if found.st_uid == os.getuid() and found.st_mode & 0o077:
        folder.chmod(OWNER_ONLY_FOLDER)


def _sync_folder(folder: Path) -> None:
    descriptor = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
