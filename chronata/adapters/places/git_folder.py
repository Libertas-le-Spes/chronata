import shutil
import subprocess
from pathlib import Path, PurePosixPath

from chronata.adapters.files.changed_files import WRITTEN_LIST, write_changed
from chronata.use_cases.ports import SaveError


def checked_folder(folder: str) -> str:
    path = PurePosixPath(folder.strip().strip("/"))
    if not path.parts or path.is_absolute() or ".." in path.parts or path.parts[0] == ".git":
        raise SaveError("give a folder inside the repository, like 'Work Logs'")
    return str(path)


class GitFolders:
    def __init__(self, copies: Path):
        self.copies = copies

    def prepare(self, place_id: str, address: str, folder: str) -> None:
        target = self._fresh_copy(place_id, address) / folder
        if target.exists() and not (target / WRITTEN_LIST).exists():
            raise SaveError(f"'{folder}' already exists in that repository and was not made by Chronata, so it is left alone; choose another folder")

    def save(self, place_id: str, address: str, folder: str, bundle: dict[str, bytes]) -> None:
        self.prepare(place_id, address, folder)
        copy = self.copies / place_id
        write_changed(copy / folder, bundle)
        self._git(copy, "add", "-A", "--", folder)
        if self._git(copy, "diff", "--cached", "--quiet").returncode == 0:
            return
        self._git(copy, "commit", "-q", "-m", f"Chronata: update {folder}")
        if self._git(copy, "push", "-q", timeout=30).returncode != 0:
            self._sync(copy)
            pushed = self._git(copy, "push", "-q", timeout=30)
            if pushed.returncode != 0:
                raise SaveError(f"could not push to {address}: {pushed.stderr.strip()}; will try again on the next save")

    def forget(self, place_id: str) -> None:
        shutil.rmtree(self.copies / place_id, ignore_errors=True)

    def _fresh_copy(self, place_id: str, address: str) -> Path:
        copy = self.copies / place_id
        if not (copy / ".git").exists():
            self.copies.mkdir(parents=True, exist_ok=True)
            cloned = self._git(self.copies, "clone", "-q", address, place_id, timeout=120)
            if cloned.returncode != 0:
                raise SaveError(f"could not reach {address}: {cloned.stderr.strip()}")
        self._sync(copy)
        return copy

    def _sync(self, copy: Path) -> None:
        pulled = self._git(copy, "pull", "-q", "--rebase", timeout=60)
        if pulled.returncode != 0:
            self._git(copy, "rebase", "--abort")
            raise SaveError(f"could not bring in the latest changes: {pulled.stderr.strip()}; will try again on the next save")

    def _git(self, where: Path, *args: str, timeout: float | None = None) -> subprocess.CompletedProcess:
        if shutil.which("git") is None:
            raise SaveError("git is not installed, so git places cannot be saved to")
        try:
            return subprocess.run(["git", "-C", str(where), *args], capture_output=True, text=True, check=False, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise SaveError("the repository did not answer in time; will try again on the next save")
