from dataclasses import dataclass
from typing import Protocol

from chronata.use_cases.ports import PlaceKindDescription


@dataclass(frozen=True)
class SavedPlace:
    id: str
    kind: str
    name: str
    target: str
    username: str = ""
    password: str = ""
    folder: str = ""


class PlaceKind(Protocol):
    id: str
    description: PlaceKindDescription

    def accept(self, place: SavedPlace) -> SavedPlace: ...
    def added(self, place: SavedPlace) -> None: ...
    def removed(self, place: SavedPlace) -> None: ...
    def deliver(self, place: SavedPlace, bundle: dict[str, bytes]) -> None: ...
    def already_there(self) -> list[SavedPlace]: ...
