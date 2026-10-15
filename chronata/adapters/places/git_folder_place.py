from dataclasses import replace

from chronata.adapters.places.git_folder import GitFolders, checked_folder
from chronata.adapters.places.place_kind import SavedPlace
from chronata.use_cases.ports import PlaceKindDescription


class GitRepositoryFolder:
    id = "git-folder"
    needs_local_history = False
    description = PlaceKindDescription(
        "Folder in a git repository", "Repository address", "https://github.com/you/notes.git", False, True, False,
        "Saves into one folder of a repository you already use, such as your notes. Only that folder is ever changed, "
        "and a folder Chronata did not create is left alone.",
    )

    def __init__(self, folders: GitFolders):
        self.folders = folders

    def accept(self, place: SavedPlace) -> SavedPlace:
        return replace(place, folder=checked_folder(place.folder))

    def added(self, place: SavedPlace) -> None:
        self.folders.prepare(place.id, place.target, place.folder)

    def removed(self, place: SavedPlace) -> None:
        self.folders.forget(place.id)

    def deliver(self, place: SavedPlace, bundle: dict[str, bytes]) -> None:
        self.folders.save(place.id, place.target, place.folder, bundle)

    def already_there(self) -> list[SavedPlace]:
        return []
