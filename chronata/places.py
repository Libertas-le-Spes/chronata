import base64
import hashlib
import json
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from chronata.audit_trail import AuditTrail

KINDS = {
    "obsidian": "Obsidian vault",
    "folder": "Folder (text file)",
    "git": "Git repository",
    "webdav": "Web server (WebDAV)",
}


class SaveError(Exception):
    pass


@dataclass(frozen=True)
class Place:
    id: str
    kind: str
    name: str
    target: str
    username: str = ""
    password: str = ""


@dataclass(frozen=True)
class SaveResult:
    place: Place
    error: str | None


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(os.environ.get("CHRONATA_CONFIG", Path(base) / "chronata"))


class PlaceBook:
    def __init__(self, directory: Path, trail: AuditTrail):
        self.path = directory / "places.json"
        self.history_path = directory / "saves.json"
        self.trail = trail
        directory.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._adopt_existing_remote()

    def places(self) -> list[Place]:
        if not self.path.exists():
            return []
        return [Place(**raw) for raw in json.loads(self.path.read_text(encoding="utf-8"))]

    def add(self, kind: str, name: str, target: str, username: str = "", password: str = "") -> Place:
        if kind not in KINDS:
            raise SaveError(f"'{kind}' is not a kind of place; choose one of {', '.join(KINDS)}")
        target = _checked_target(kind, target.strip())
        place = Place(f"{kind}-{secrets.token_hex(3)}", kind, name.strip() or KINDS[kind], target, username.strip(), password)
        if kind == "git":
            self.trail.add_remote(place.id, target)
        self._write([*self.places(), place])
        return place

    def remove(self, place_id: str) -> Place:
        place = next((p for p in self.places() if p.id == place_id), None)
        if place is None:
            raise SaveError(f"there is no place {place_id}")
        if place.kind == "git" and place.id != "origin":
            self.trail.remove_remote(place.id)
        self._write([p for p in self.places() if p.id != place_id])
        return place

    def history(self) -> dict:
        return json.loads(self.history_path.read_text(encoding="utf-8")) if self.history_path.exists() else {}

    def remember(self, outcome: SaveResult, when: datetime, uploaded: dict[str, str] | None = None) -> None:
        history = self.history()
        entry = history.get(outcome.place.id, {})
        entry["attempted"] = when.isoformat()
        entry["error"] = outcome.error
        if outcome.error is None:
            entry["saved"] = when.isoformat()
        if uploaded is not None:
            entry["uploaded"] = uploaded
        history[outcome.place.id] = entry
        self.history_path.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")

    def _adopt_existing_remote(self) -> None:
        remote = self.trail.remote()
        if remote:
            name = "GitHub" if "github.com" in remote else "Git repository"
            self._write([Place("origin", "git", name, remote)])

    def _write(self, places: list[Place]) -> None:
        self.path.write_text(json.dumps([asdict(p) for p in places], indent=2) + "\n", encoding="utf-8")
        self.path.chmod(0o600)


def save(place: Place, bundle: dict[str, bytes], trail: AuditTrail, uploaded: dict[str, str]) -> dict[str, str]:
    match place.kind:
        case "git":
            failure = trail.push(place.id, timeout=20)
            if failure:
                raise SaveError(failure)
            return uploaded
        case "obsidian":
            _write_folder(Path(place.target) / "Chronata", bundle)
            return uploaded
        case "folder":
            _write_folder(Path(place.target), bundle)
            return uploaded
        case "webdav":
            return _upload(place, bundle, uploaded)
    raise SaveError(f"unknown kind of place: {place.kind}")


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


def _write_folder(folder: Path, bundle: dict[str, bytes]) -> None:
    try:
        for relative, content in bundle.items():
            path = folder / relative
            if path.exists() and path.read_bytes() == content:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.name}.chronata-tmp")
            temporary.write_bytes(content)
            os.replace(temporary, path)
    except OSError as error:
        raise SaveError(f"could not write to {folder}: {error.strerror or error}")


def _upload(place: Place, bundle: dict[str, bytes], uploaded: dict[str, str]) -> dict[str, str]:
    base = place.target.rstrip("/") + "/Chronata/"
    sent = dict(uploaded)
    made_folders: set[str] = set()
    for relative, content in sorted(bundle.items()):
        digest = hashlib.sha256(content).hexdigest()
        if sent.get(relative) == digest:
            continue
        parts = relative.split("/")[:-1]
        for depth in range(len(parts) + 1):
            folder = "/".join(parts[:depth])
            if folder not in made_folders:
                _dav(place, "MKCOL", base + _quoted(folder) + ("/" if folder else ""), None, accept=(201, 301, 405))
                made_folders.add(folder)
        _dav(place, "PUT", base + _quoted(relative), content, accept=(200, 201, 204))
        sent[relative] = digest
    return sent


def _dav(place: Place, method: str, url: str, body: bytes | None, accept: tuple[int, ...]) -> None:
    request = urllib.request.Request(url, data=body, method=method)
    if place.username:
        token = base64.b64encode(f"{place.username}:{place.password}".encode()).decode()
        request.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
        error.close()
    except (urllib.error.URLError, OSError) as error:
        raise SaveError(f"could not reach {place.target}: {getattr(error, 'reason', error)}")
    if status in (401, 403):
        raise SaveError(f"{place.target} refused the username or password")
    if status not in accept:
        raise SaveError(f"{place.target} answered {status} to {method} {url}")


def _quoted(relative: str) -> str:
    return "/".join(urllib.parse.quote(part) for part in relative.split("/") if part)
