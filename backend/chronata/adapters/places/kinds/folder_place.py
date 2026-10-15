from dataclasses import replace
from pathlib import Path

from chronata.adapters.places.place_kind import SavedPlace
from chronata.adapters.storage.changed_files import write_changed
from chronata.use_cases.log.ports import PlaceKindDescription, SaveError


class FolderPlace:
    id = "folder"
    needs_local_history = False
    description = PlaceKindDescription(
        "Folder", "Folder", "/home/you/Documents/Time", True, False, False,
        "Gets an overview, the whole log in one file, a file per day, and the sealed log. A Dropbox, OneDrive or Syncthing folder works too.",
    )

    def accept(self, place: SavedPlace) -> SavedPlace:
        folder = Path(place.target).expanduser()
        if not folder.is_dir():
            raise SaveError(f"{folder} is not a folder on this computer")
        return replace(place, target=str(folder), folder="")

    def added(self, place: SavedPlace) -> None:
        return None

    def removed(self, place: SavedPlace) -> None:
        return None

    def deliver(self, place: SavedPlace, bundle: dict[str, bytes]) -> None:
        if not Path(place.target).is_dir():
            raise SaveError(f"{place.target} is missing; if it is on a drive that is not plugged in, plug it in and save again")
        write_changed(self.destination(place), bundle)

    def already_there(self) -> list[SavedPlace]:
        return []

    def destination(self, place: SavedPlace) -> Path:
        return Path(place.target)


class ObsidianVault(FolderPlace):
    id = "obsidian"
    description = PlaceKindDescription(
        "Obsidian vault", "Vault folder", "/home/you/Notes", True, False, False,
        "Goes into a Chronata folder inside the vault: an overview, the whole log in one note, a note per day, and the sealed log.",
    )

    def accept(self, place: SavedPlace) -> SavedPlace:
        accepted = super().accept(place)
        if not (Path(accepted.target) / ".obsidian").is_dir():
            raise SaveError(f"{accepted.target} is a folder, but not an Obsidian vault (it has no .obsidian folder inside)")
        return accepted

    def destination(self, place: SavedPlace) -> Path:
        return Path(place.target) / "Chronata"
