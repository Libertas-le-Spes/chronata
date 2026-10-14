import shutil
import subprocess
from pathlib import Path

from chronata.use_cases.ports import SaveError


class GitRemotes:
    def __init__(self, repository: Path):
        self.repository = repository

    def address(self, name: str = "origin") -> str | None:
        if shutil.which("git") is None or not (self.repository / ".git").exists():
            return None
        found = self._git("remote", "get-url", name)
        return found.stdout.strip() if found.returncode == 0 else None

    def add(self, name: str, address: str) -> None:
        if not (self.repository / ".git").exists():
            self._git("init", "-q", "-b", "main")
        added = self._git("remote", "add", name, address)
        if added.returncode != 0:
            raise SaveError(f"could not add {address}: {added.stderr.strip()}")

    def remove(self, name: str) -> None:
        self._git("remote", "remove", name)

    def push(self, name: str) -> None:
        try:
            pushed = self._git("push", "-q", name, "HEAD:main", timeout=20)
        except subprocess.TimeoutExpired:
            raise SaveError("did not answer in 20s; will try again on the next save")
        if pushed.returncode != 0:
            raise SaveError(f"{pushed.stderr.strip() or 'push failed'}; will try again on the next save")

    def _git(self, *args: str, timeout: float | None = None) -> subprocess.CompletedProcess:
        if shutil.which("git") is None:
            raise SaveError("git is not installed, so git places cannot be saved to")
        return subprocess.run(["git", "-C", str(self.repository), *args], capture_output=True, text=True, check=False, timeout=timeout)
