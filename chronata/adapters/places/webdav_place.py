import re
from dataclasses import replace

from chronata.adapters.places.place_kind import SavedPlace
from chronata.adapters.places.save_record import SaveRecord
from chronata.adapters.places.webdav_upload import upload_changed
from chronata.use_cases.ports import PlaceKindDescription, SaveError


class WebDavServer:
    id = "webdav"
    description = PlaceKindDescription(
        "Web server (WebDAV)", "Server address", "https://cloud.example.com/remote.php/dav/files/you/", False, False, True,
        "Nextcloud, ownCloud and most file servers speak WebDAV. The password is kept only on this computer.",
    )

    def __init__(self, save_record: SaveRecord):
        self.save_record = save_record

    def accept(self, place: SavedPlace) -> SavedPlace:
        if not re.match(r"^https?://", place.target):
            raise SaveError("a web server address starts with https://")
        return replace(place, folder="")

    def added(self, place: SavedPlace) -> None:
        return None

    def removed(self, place: SavedPlace) -> None:
        return None

    def deliver(self, place: SavedPlace, bundle: dict[str, bytes]) -> None:
        already_sent = self.save_record.last(place.id).get("uploaded", {})
        self.save_record.note(place.id, uploaded=upload_changed(place.target, place.username, place.password, bundle, already_sent))

    def already_there(self) -> list[SavedPlace]:
        return []
