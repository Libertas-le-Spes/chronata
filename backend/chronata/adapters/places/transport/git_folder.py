import shutil
import subprocess
from pathlib import Path, PurePosixPath

from chronata.adapters.places.save_record import SaveRecord
from chronata.adapters.storage.changed_files import WRITTEN_LIST, listing, write_changed
from chronata.adapters.storage.owner_only_file import make_owner_only_folder
from chronata.adapters.storage.place_folder import PlaceFolder
from chronata.use_cases.log.ports import SaveError


def checked_folder(folder: str) -> str:
    path = PurePosixPath(folder.strip().strip("/"))
    if not _inside_the_repository(path):
        raise SaveError("give a folder inside the repository, like 'Work Logs'")
    return str(path)


def _inside_the_repository(path: PurePosixPath) -> bool:
    if not path.parts or path.is_absolute():
        return False
    return ".." not in path.parts and path.parts[0] != ".git"


class GitFolders:
    def __init__(self, copies: Path, save_record: SaveRecord):
        self.copies = copies
        self.save_record = save_record

    def prepare(self, place_id: str, address: str, folder: str) -> None:
        target = self._fresh_copy(place_id, address, folder) / folder
        if target.exists() and not (target / WRITTEN_LIST).exists():
            raise SaveError(f"'{folder}' already exists in that repository and was not made by Chronata, so it is left alone; choose another folder")

    def save(self, place_id: str, address: str, folder: str, bundle: dict[str, bytes]) -> None:
        self.prepare(place_id, address, folder)
        copy = self.copies / place_id
        place_folder = PlaceFolder(copy, folder)
        write_changed(place_folder, bundle, self.save_record.written_to(place_id))
        place_folder.write(WRITTEN_LIST, listing(set(bundle)))
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

    def _fresh_copy(self, place_id: str, address: str, folder: str) -> Path:
        make_owner_only_folder(self.copies)
        copy = self.copies / place_id
        if not (copy / ".git").exists():
            self._partial_copy(place_id, address)
        self._git(copy, "sparse-checkout", "set", folder)
        self._git(copy, "checkout", "-q")
        self._sync(copy)
        return copy

    def _partial_copy(self, place_id: str, address: str) -> None:
        make_owner_only_folder(self.copies)
        cloned = self._git(self.copies, "clone", "-q", "--filter=blob:none", "--no-checkout", address, place_id, timeout=120)
        if cloned.returncode != 0:
            raise SaveError(f"could not reach {address}: {cloned.stderr.strip()}")

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
