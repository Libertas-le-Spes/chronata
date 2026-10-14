import fcntl
from contextlib import contextmanager
from pathlib import Path


def write_lock(path: Path):
    @contextmanager
    def locked():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield
    return locked
