import sys
from contextlib import contextmanager
from pathlib import Path

if sys.platform == "win32":
    import msvcrt

    def _hold(handle) -> None:
        handle.seek(0)
        while True:
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                return
            except OSError:
                continue

    def _release(handle) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _hold(handle) -> None:
        fcntl.flock(handle, fcntl.LOCK_EX)

    def _release(handle) -> None:
        fcntl.flock(handle, fcntl.LOCK_UN)


def write_lock(path: Path):
    @contextmanager
    def locked():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a+") as handle:
            _hold(handle)
            try:
                yield
            finally:
                _release(handle)
    return locked
