from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from chronata.adapters.files import data_folder
from chronata.adapters.files.data_folder import DataFolder, find_saved_copy
from chronata.adapters.files.ledger_file import LedgerFile
from chronata.adapters.files.working_day_file import WorkingDayFile
from chronata.adapters.files.write_lock import write_lock
from chronata.adapters.git.history import GitHistory
from chronata.adapters.linux.desktop import LinuxDesktop
from chronata.adapters.linux.power_journal import PowerJournal
from chronata.adapters.places import place_book
from chronata.adapters.places.place_book import PlaceBook
from chronata.adapters.timestamping.rfc3161 import Rfc3161Timestamper
from chronata.presenters.daily_notes import daily_notes, overview, text_log
from chronata.use_cases.ports import Clock, Desktop, PowerHistory, Timestamper
from chronata.use_cases.saving import Saving
from chronata.use_cases.timesheet import Timesheet


@dataclass(frozen=True)
class App:
    sheet: Timesheet
    saving: Saving
    git: GitHistory
    timestamper: Timestamper
    desktop: Desktop
    power: PowerHistory


def local_now() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


def open_app(data: Path | None = None, config: Path | None = None, clock: Clock = local_now,
             power: PowerHistory | None = None, timestamper: Timestamper | None = None, desktop: Desktop | None = None) -> App:
    folder = DataFolder(data or data_folder.default_location())
    git = GitHistory(folder.directory, data_folder.LEDGER)
    power = power or PowerJournal()
    timestamper = timestamper or Rfc3161Timestamper(folder.timestamps)
    sheet = Timesheet(LedgerFile(folder.ledger), git, WorkingDayFile(folder.working_day), power, write_lock(folder.lock), clock)

    def readable_copies(current: Timesheet, now: datetime) -> dict[str, dict[str, bytes]]:
        days = daily_notes(current.shifts(), current.weeks(), current.pc_sessions(), now)
        stamps, entries = timestamper.stamps(), current.entry_count()
        notes = {f"Days/{day:%Y-%m-%d}.md": note.encode() for day, note in days.items()}
        notes["Chronata.md"] = overview(stamps, entries).encode()
        return {"obsidian": notes, "webdav": notes, "folder": {"Chronata time log.txt": text_log(days, stamps, entries).encode()}}

    saving = Saving(PlaceBook(config or place_book.default_location(), git), timestamper, git, folder.sealed_files, readable_copies)
    sheet.publish = saving
    return App(sheet, saving, git, timestamper, desktop or LinuxDesktop(), power)


def open_saved_copy(folder: Path) -> tuple[LedgerFile, Rfc3161Timestamper]:
    sealed = find_saved_copy(folder)
    return LedgerFile(sealed / data_folder.LEDGER), Rfc3161Timestamper(sealed / data_folder.TIMESTAMPS)
