import fcntl
import os
from contextlib import contextmanager

from chronata.adapters.storage.owner_only_folder import OwnerOnlyFolder


def write_lock(folder: OwnerOnlyFolder, name: str):
    @contextmanager
    def locked():
        descriptor = folder.open_for_locking(name)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            os.close(descriptor)
    return locked
