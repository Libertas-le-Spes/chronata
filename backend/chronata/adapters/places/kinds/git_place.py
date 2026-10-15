from dataclasses import replace

from chronata.adapters.places.place_kind import SavedPlace
from chronata.adapters.places.transport.git_push import GitRemotes
from chronata.use_cases.log.ports import PlaceKindDescription

FIRST_REMOTE = "origin"


class GitRepository:
    id = "git"
    needs_local_history = True
    description = PlaceKindDescription(
        "Git repository", "Repository address", "https://github.com/you/time-log.git", False, False, False,
        "Create an empty private repository first. Git hosts record when each save arrives.",
    )

    def __init__(self, remotes: GitRemotes):
        self.remotes = remotes

    def accept(self, place: SavedPlace) -> SavedPlace:
        return replace(place, folder="")

    def added(self, place: SavedPlace) -> None:
        self.remotes.add(place.id, place.target)

    def removed(self, place: SavedPlace) -> None:
        if place.id != FIRST_REMOTE:
            self.remotes.remove(place.id)

    def deliver(self, place: SavedPlace, bundle: dict[str, bytes]) -> None:
        self.remotes.push(place.id)

    def already_there(self) -> list[SavedPlace]:
        remote = self.remotes.address(FIRST_REMOTE)
        if not remote:
            return []
        return [SavedPlace(FIRST_REMOTE, self.id, "GitHub" if "github.com" in remote else self.description.label, remote)]
