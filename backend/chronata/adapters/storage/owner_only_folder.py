import errno
import os
import secrets
import stat
from pathlib import Path

from chronata.use_cases.log.ports import NotPrivate

OTHERS_MAY_TOUCH = 0o077


class OwnerOnlyFolder:
    def __init__(self, path: Path):
        self.path = path

    def write(self, name: str, text: str) -> None:
        self._make_private()
        temporary = self.path / f".{name}.{secrets.token_hex(8)}"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(text)
        os.replace(temporary, self.path / name)

    def read(self, name: str) -> str | None:
        try:
            _require_private(os.lstat(self.path), self.path, stat.S_ISDIR)
            descriptor = os.open(self.path / name, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return None
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise NotPrivate(f"{self.path / name} is a link, so Chronata will not trust it as its page key; remove it") from error
            raise
        with os.fdopen(descriptor, encoding="utf-8") as file:
            _require_private(os.fstat(file.fileno()), self.path / name, stat.S_ISREG)
            return file.read()

    def open_for_locking(self, name: str) -> int:
        self._make_private()
        descriptor = os.open(self.path / name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            _require_private(os.fstat(descriptor), self.path / name, stat.S_ISREG)
        except NotPrivate:
            os.close(descriptor)
            raise
        return descriptor

    def _make_private(self) -> None:
        self.path.mkdir(mode=0o700, parents=True, exist_ok=True)
        _require_private(os.lstat(self.path), self.path, stat.S_ISDIR)


def _require_private(found: os.stat_result, path: Path, right_kind) -> None:
    if not right_kind(found.st_mode) or found.st_uid != os.getuid() or found.st_mode & OTHERS_MAY_TOUCH:
        raise NotPrivate(f"{path} is not private to you, so Chronata will not keep its keys and locks there; "
                         f"remove it, or make it yours alone with: chmod go-rwx {path}")
