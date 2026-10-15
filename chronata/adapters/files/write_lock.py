import fcntl
from contextlib import contextmanager
from pathlib import Path


def write_lock(path: Path):
    @contextmanager
    def locked():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
    return locked
