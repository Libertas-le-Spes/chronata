from datetime import datetime
from typing import Callable

from chronata.timekeeping.stamps import Stamp, latest
from chronata.use_cases.outcome import Outcome, UserError
from chronata.use_cases.ports import History, Place, Places, SaveError, Timestamper

ReadableCopies = Callable[[object, datetime], dict[str, dict[str, bytes]]]


class Saving:
    def __init__(self, places: Places, timestamper: Timestamper, history: History,
                 sealed_files: Callable[[], dict[str, bytes]], readable_copies: ReadableCopies):
        self.places = places
        self.timestamper = timestamper
        self.history = history
        self.sealed_files = sealed_files
        self.readable_copies = readable_copies

    def __call__(self, sheet) -> str | None:
        warnings = []
        head = sheet.record.head()
        if head:
            made, failures = self.timestamper.stamp(*head)
            if made:
                self.history.commit(f"timestamped entry {head[0]} by {', '.join(s.authority_name for s in made)}")
            if failures:
                warnings.append(f"timestamp not taken ({'; '.join(failures)}); will try again on the next save")
        self.history.commit("brought the history up to date before saving")
        warnings += self._save_everywhere(sheet)
        return "; ".join(warnings) or None

    def add_place(self, sheet, kind: str, name: str, target: str, username: str = "", password: str = "") -> Outcome:
        try:
            place = self.places.add(kind, name, target, username, password)
        except SaveError as error:
            raise UserError(str(error))
        saved = sheet.save_now()
        return Outcome(f"added {place.name} and {saved.message}", saved.warning)

    def remove_place(self, place_id: str) -> Outcome:
        try:
            place = self.places.remove(place_id)
        except SaveError as error:
            raise UserError(str(error))
        return Outcome(f"removed {place.name}; copies already saved there are left as they are", None)

    def statuses(self) -> list[tuple[Place, dict]]:
        return [(place, self.places.last_save(place.id)) for place in self.places.places()]

    def stamped(self) -> tuple[int | None, list[Stamp]]:
        return latest(self.timestamper.stamps())

    def _save_everywhere(self, sheet) -> list[str]:
        targets = self.places.places()
        if not targets:
            return ["only saved on this computer; add a place to keep a copy somewhere else"]
        now = sheet.clock()
        sealed = self.sealed_files()
        readable = self.readable_copies(sheet, now)
        warnings = []
        for place in targets:
            try:
                self.places.deliver(place, {**sealed, **readable.get(place.kind, {})})
                self.places.remember(place.id, now, None)
            except SaveError as error:
                self.places.remember(place.id, now, str(error))
                warnings.append(f"not saved to {place.name}: {error}")
        return warnings
