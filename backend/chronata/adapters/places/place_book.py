import json
import secrets
from dataclasses import asdict, fields, replace
from pathlib import Path

from chronata.adapters.places.place_kind import PlaceKind, SavedPlace
from chronata.adapters.storage.owner_only_file import make_owner_only_folder, write_owner_only
from chronata.use_cases.log.ports import PlaceKindDescription, SaveError

KEPT = {field.name for field in fields(SavedPlace)}


class PlaceBook:
    def __init__(self, directory: Path, kinds: list[PlaceKind]):
        make_owner_only_folder(directory)
        self.path = directory / "places.json"
        self.by_kind = {kind.id: kind for kind in kinds}
        if not self.path.exists():
            self._write([place for kind in kinds for place in kind.already_there()])
        self._forget_passwords_kept_in_plain_text()

    def kinds(self) -> dict[str, PlaceKindDescription]:
        return {kind_id: kind.description for kind_id, kind in self.by_kind.items()}

    def places(self) -> list[SavedPlace]:
        if not self.path.exists():
            return []
        return [SavedPlace(**{key: value for key, value in raw.items() if key in KEPT}) for raw in self._raw()]

    def add(self, kind: str, name: str, target: str, username: str = "", password: str = "", folder: str = "") -> SavedPlace:
        if kind not in self.by_kind:
            raise SaveError(f"'{kind}' is not a kind of place; choose one of {', '.join(self.by_kind)}")
        if not target.strip():
            raise SaveError("say where to save: a folder, or an address")
        chosen = self.by_kind[kind]
        typed = SavedPlace(f"{kind}-{secrets.token_hex(3)}", kind, name.strip(), target.strip(), username.strip(), folder)
        place = chosen.accept(typed)
        place = replace(place, name=place.name or chosen.description.label)
        chosen.added(place, password)
        self._write([*self.places(), place])
        return place

    def remove(self, place_id: str) -> SavedPlace:
        place = next((p for p in self.places() if p.id == place_id), None)
        if place is None:
            raise SaveError(f"there is no place {place_id}")
        self._kind_of(place).removed(place)
        self._write([p for p in self.places() if p.id != place_id])
        return place

    def needs_local_history(self) -> bool:
        return any(self._kind_of(place).needs_local_history for place in self.places())

    def deliver(self, place: SavedPlace, bundle: dict[str, bytes]) -> None:
        self._kind_of(place).deliver(place, bundle)

    def _kind_of(self, place: SavedPlace) -> PlaceKind:
        if place.kind not in self.by_kind:
            raise SaveError(f"unknown kind of place: {place.kind}")
        return self.by_kind[place.kind]

    def _forget_passwords_kept_in_plain_text(self) -> None:
        if any("password" in raw for raw in self._raw()):
            self._write(self.places())

    def _raw(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else []

    def _write(self, places: list[SavedPlace]) -> None:
        write_owner_only(self.path, (json.dumps([asdict(p) for p in places], indent=2) + "\n").encode("utf-8"))
