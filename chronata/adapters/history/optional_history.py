import shutil
from pathlib import Path
from typing import Callable

from chronata.adapters.history.git_history import GitHistory


class OptionalHistory:
    def __init__(self, directory: Path, watched_file: str, wanted: Callable[[], bool]):
        self.directory = directory
        self.watched_file = watched_file
        self.wanted = wanted
        self._git: GitHistory | None = None

    def keeps_history(self) -> bool:
        return self._active() is not None

    def commit(self, message: str) -> None:
        active = self._active()
        if active:
            active.commit(message)

    def rewrites(self) -> list[str]:
        active = self._active()
        return active.rewrites() if active else []

    def _active(self) -> GitHistory | None:
        if not self.wanted() or shutil.which("git") is None:
            return None
        if self._git is None:
            self._git = GitHistory(self.directory, self.watched_file)
        return self._git
