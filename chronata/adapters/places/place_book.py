import json
import os
import re
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from chronata.adapters.files.changed_files import write_changed
from chronata.adapters.places.git_folder import GitFolders, checked_folder
from chronata.adapters.places.git_push import GitRemotes
from chronata.adapters.places.webdav_upload import upload_changed
from chronata.use_cases.ports import SaveError

KINDS = {
    "obsidian": "Obsidian vault",
    "folder": "Folder",
    "git": "Git repository",
    "git-folder": "Folder in a git repository",
    "webdav": "Web server (WebDAV)",
}


@dataclass(frozen=True)
class SavedPlace:
    id: str
    kind: str
    name: str
    target: str
    username: str = ""
    password: str = ""
    folder: str = ""


def default_location() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(os.environ.get("CHRONATA_CONFIG", Path(base) / "chronata"))


class PlaceBook:
    def __init__(self, directory: Path, git_remotes: GitRemotes, git_folders: GitFolders):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "places.json"
        self.saves_path = directory / "saves.json"
        self.git_remotes = git_remotes
        self.git_folders = git_folders
        if not self.path.exists():
            self._adopt_existing_remote()

    def kinds(self) -> dict[str, str]:
        return KINDS

    def places(self) -> list[SavedPlace]:
        if not self.path.exists():
            return []
        return [SavedPlace(**raw) for raw in json.loads(self.path.read_text(encoding="utf-8"))]

    def add(self, kind: str, name: str, target: str, username: str = "", password: str = "", folder: str = "") -> SavedPlace:
        if kind not in KINDS:
            raise SaveError(f"'{kind}' is not a kind of place; choose one of {', '.join(KINDS)}")
        target = _checked_target(kind, target.strip())
        folder = checked_folder(folder) if kind == "git-folder" else ""
        place = SavedPlace(f"{kind}-{secrets.token_hex(3)}", kind, name.strip() or KINDS[kind], target, username.strip(), password, folder)
        if kind == "git":
            self.git_remotes.add(place.id, target)
        if kind == "git-folder":
            self.git_folders.prepare(place.id, target, folder)
        self._write([*self.places(), place])
        return place

    def remove(self, place_id: str) -> SavedPlace:
        place = next((p for p in self.places() if p.id == place_id), None)
        if place is None:
            raise SaveError(f"there is no place {place_id}")
        if place.kind == "git" and place.id != "origin":
            self.git_remotes.remove(place.id)
        if place.kind == "git-folder":
            self.git_folders.forget(place.id)
        self._write([p for p in self.places() if p.id != place_id])
        return place

    def deliver(self, place: SavedPlace, bundle: dict[str, bytes]) -> None:
        if place.kind in ("obsidian", "folder") and not Path(place.target).is_dir():
            raise SaveError(f"{place.target} is missing; if it is on a drive that is not plugged in, plug it in and save again")
        match place.kind:
            case "git":
                self.git_remotes.push(place.id)
            case "git-folder":
                self.git_folders.save(place.id, place.target, place.folder, bundle)
            case "obsidian":
                write_changed(Path(place.target) / "Chronata", bundle)
            case "folder":
                write_changed(Path(place.target), bundle)
            case "webdav":
                sent = upload_changed(place.target, place.username, place.password, bundle, self.last_save(place.id).get("uploaded", {}))
                self._update(place.id, uploaded=sent)
            case _:
                raise SaveError(f"unknown kind of place: {place.kind}")

    def last_save(self, place_id: str) -> dict:
        return self._saves().get(place_id, {})

    def remember(self, place_id: str, when: datetime, error: str | None) -> None:
        self._update(place_id, attempted=when.isoformat(), error=error, **({} if error else {"saved": when.isoformat()}))

    def _update(self, place_id: str, **fields) -> None:
        saves = self._saves()
        saves[place_id] = {**saves.get(place_id, {}), **fields}
        self.saves_path.write_text(json.dumps(saves, indent=2) + "\n", encoding="utf-8")

    def _saves(self) -> dict:
        return json.loads(self.saves_path.read_text(encoding="utf-8")) if self.saves_path.exists() else {}

    def _adopt_existing_remote(self) -> None:
        remote = self.git_remotes.address()
        if remote:
            self._write([SavedPlace("origin", "git", "GitHub" if "github.com" in remote else "Git repository", remote)])

    def _write(self, places: list[SavedPlace]) -> None:
        self.path.write_text(json.dumps([asdict(p) for p in places], indent=2) + "\n", encoding="utf-8")
        self.path.chmod(0o600)


def _checked_target(kind: str, target: str) -> str:
    if not target:
        raise SaveError("say where to save: a folder, or an address")
    if kind in ("obsidian", "folder"):
        folder = Path(target).expanduser()
        if not folder.is_dir():
            raise SaveError(f"{folder} is not a folder on this computer")
        if kind == "obsidian" and not (folder / ".obsidian").is_dir():
            raise SaveError(f"{folder} is a folder, but not an Obsidian vault (it has no .obsidian folder inside)")
        return str(folder)
    if kind == "webdav" and not re.match(r"^https?://", target):
        raise SaveError("a web server address starts with https://")
    return target
