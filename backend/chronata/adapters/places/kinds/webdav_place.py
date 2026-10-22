from dataclasses import replace

from chronata.adapters.places.addresses import checked_web_address
from chronata.adapters.places.place_kind import SavedPlace
from chronata.adapters.places.save_record import SaveRecord
from chronata.adapters.places.transport.webdav_upload import upload_changed
from chronata.use_cases.log.ports import PlaceKindDescription, SaveError, Secrets


class WebDavServer:
    id = "webdav"
    needs_local_history = False
    description = PlaceKindDescription(
        "Web server (WebDAV)", "Server address", "https://cloud.example.com/remote.php/dav/files/you/", False, False, True,
        "Nextcloud, ownCloud and most file servers speak WebDAV. The password is kept in your desktop keyring, on this computer only.",
    )

    def __init__(self, save_record: SaveRecord, secrets: Secrets):
        self.save_record = save_record
        self.secrets = secrets

    def accept(self, place: SavedPlace) -> SavedPlace:
        return replace(place, target=checked_web_address(place.target), folder="")

    def added(self, place: SavedPlace, password: str) -> None:
        if place.username and not password:
            raise SaveError("give the password for that name")
        self.take_password(place, password)

    def take_password(self, place: SavedPlace, password: str) -> None:
        if password:
            self.secrets.keep(place.id, password)

    def removed(self, place: SavedPlace) -> None:
        self.secrets.forget(place.id)

    def deliver(self, place: SavedPlace, bundle: dict[str, bytes]) -> None:
        password = self.secrets.find(place.id) if place.username else ""
        if place.username and password is None:
            raise SaveError("its password is not in the desktop keyring yet; unlock the keyring, or install secret-tool, and save again")
        already_sent = self.save_record.last(place.id).get("uploaded", {})
        self.save_record.note(place.id, uploaded=upload_changed(place.target, place.username, password, bundle, already_sent))

    def already_there(self) -> list[SavedPlace]:
        return []
