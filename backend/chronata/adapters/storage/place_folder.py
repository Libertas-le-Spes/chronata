import errno
import os
import secrets
import stat
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from chronata.adapters.storage.owner_only_file import OWNER_ONLY, OWNER_ONLY_FOLDER
from chronata.use_cases.log.ports import SaveError


class PlaceFolder:
    def __init__(self, base: Path, inside: str = ""):
        self.base = base
        self.inside = _parts(inside) if inside else ()

    def __str__(self) -> str:
        return str(self.base.joinpath(*self.inside))

    def holds(self, relative: str, content: bytes) -> bool:
        *folders, name = _parts(relative)
        try:
            with self._folder(folders, create=False) as folder:
                return _read(folder, name) == content
        except FileNotFoundError:
            return False

    def write(self, relative: str, content: bytes) -> None:
        *folders, name = _parts(relative)
        with self._folder(folders, create=True) as folder:
            temporary = f".{name}.{secrets.token_hex(8)}.chronata-tmp"
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, OWNER_ONLY, dir_fd=folder)
            with os.fdopen(descriptor, "wb") as file:
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, name, src_dir_fd=folder, dst_dir_fd=folder)
            os.fsync(folder)

    def remove(self, relative: str) -> None:
        *folders, name = _parts(relative)
        try:
            with self._folder(folders, create=False) as folder:
                if stat.S_ISREG(os.stat(name, dir_fd=folder, follow_symlinks=False).st_mode):
                    os.unlink(name, dir_fd=folder)
        except FileNotFoundError:
            return
        self._remove_emptied(folders)

    def _remove_emptied(self, folders: list[str]) -> None:
        for depth in range(len(folders), 0, -1):
            try:
                with self._folder(folders[:depth - 1], create=False) as parent:
                    os.rmdir(folders[depth - 1], dir_fd=parent)
            except FileNotFoundError:
                continue
            except OSError as error:
                if error.errno in (errno.ENOTEMPTY, errno.EEXIST, errno.ENOTDIR):
                    return
                raise

    @contextmanager
    def _folder(self, folders: list[str], create: bool):
        if create:
            self.base.mkdir(mode=OWNER_ONLY_FOLDER, parents=True, exist_ok=True)
        current = os.open(self.base, os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in (*self.inside, *folders):
                inner = _step_into(current, part, create)
                os.close(current)
                current = inner
            yield current
        finally:
            os.close(current)


def _step_into(folder: int, part: str, create: bool) -> int:
    if create:
        try:
            os.mkdir(part, OWNER_ONLY_FOLDER, dir_fd=folder)
        except FileExistsError:
            pass
    try:
        return os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=folder)
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR):
            raise SaveError(f"'{part}' is a link or a file where Chronata keeps a folder, so nothing was written there") from error
        raise


def _read(folder: int, name: str) -> bytes | None:
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=folder)
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOENT):
            return None
        raise
    with os.fdopen(descriptor, "rb") as file:
        return file.read() if stat.S_ISREG(os.fstat(file.fileno()).st_mode) else None


def _parts(relative: str) -> tuple[str, ...]:
    path = PurePosixPath(relative)
    parts = path.parts
    if not parts or path.is_absolute() or any(part in ("", ".", "..") or "\0" in part or "\\" in part for part in parts):
        raise SaveError(f"'{relative}' is not a name inside the place, so it was left alone")
    return parts
