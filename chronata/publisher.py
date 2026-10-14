from datetime import datetime
from pathlib import Path

from chronata import places, readable, timestamps
from chronata.places import PlaceBook, SaveError, SaveResult

SEALED_FILES = ["ledger.jsonl", "rules.json"]


class Publisher:
    def __init__(self, book: PlaceBook):
        self.book = book

    def __call__(self, sheet) -> str | None:
        warnings = []
        head = sheet.ledger.head()
        if head:
            made, failures = timestamps.stamp_head(sheet.directory, *head)
            if made:
                sheet.trail.commit(f"timestamped entry {head[0]} by {', '.join(s.authority_name for s in made)}")
            if failures:
                warnings.append(f"timestamp not taken ({'; '.join(failures)}); will try again on the next save")
        warnings += self.save_everywhere(sheet)
        return "; ".join(warnings) or None

    def save_everywhere(self, sheet) -> list[str]:
        saved_places = self.book.places()
        if not saved_places:
            return ["only saved on this computer; add a place to keep a copy somewhere else"]
        now = sheet.clock()
        history = self.book.history()
        sealed = _sealed(sheet.directory)
        notes = _notes(sheet, now)
        warnings = []
        for place in saved_places:
            bundle = {**sealed, **notes.get(place.kind, {})}
            try:
                uploaded = places.save(place, bundle, sheet.trail, history.get(place.id, {}).get("uploaded", {}))
                self.book.remember(SaveResult(place, None), now, uploaded if place.kind == "webdav" else None)
            except SaveError as error:
                self.book.remember(SaveResult(place, str(error)), now)
                warnings.append(f"not saved to {place.name}: {error}")
        return warnings


def _sealed(directory: Path) -> dict[str, bytes]:
    files = {f"sealed/{name}": (directory / name).read_bytes() for name in SEALED_FILES if (directory / name).exists()}
    for stamp in timestamps.stamps(directory):
        files[f"sealed/{timestamps.FOLDER}/{stamp.path.name}"] = stamp.path.read_bytes()
    return files


def _notes(sheet, now: datetime) -> dict[str, dict[str, bytes]]:
    days = readable.daily_notes(sheet.shifts(), sheet.weeks(), sheet.pc_sessions(), sheet.rules, now)
    stamps = timestamps.stamps(sheet.directory)
    entries = len(sheet.ledger.entries())
    as_markdown = {f"Days/{day:%Y-%m-%d}.md": note.encode() for day, note in days.items()}
    as_markdown["Chronata.md"] = readable.overview(stamps, entries).encode()
    return {
        "obsidian": as_markdown,
        "webdav": as_markdown,
        "folder": {"Chronata time log.txt": readable.text_log(days, stamps, entries).encode()},
    }
