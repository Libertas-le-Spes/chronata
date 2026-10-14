from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from chronata.adapters.files import data_folder
from chronata.adapters.files.data_folder import DataFolder, find_saved_copy
from chronata.adapters.files.ledger_file import LedgerFile
from chronata.adapters.files.working_day_file import WorkingDayFile
from chronata.adapters.files.write_lock import write_lock
from chronata.adapters.history.optional_history import OptionalHistory
from chronata.adapters.linux.desktop import LinuxDesktop
from chronata.adapters.linux.power_journal import PowerJournal
from chronata.adapters.places import place_book
from chronata.adapters.places.git_folder import GitFolders
from chronata.adapters.places.git_push import GitRemotes
from chronata.adapters.places.place_book import PlaceBook
from chronata.adapters.timestamping.rfc3161 import Rfc3161Timestamper
from chronata.presenters.readable_copy import readable_files
from chronata.use_cases.ports import Clock, Desktop, History, PowerHistory, Timestamper
from chronata.use_cases.saving import Saving
from chronata.use_cases.timesheet import Timesheet


@dataclass(frozen=True)
class App:
    sheet: Timesheet
    saving: Saving
    history: History
    timestamper: Timestamper
    desktop: Desktop
    power: PowerHistory


def local_now() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


def open_app(data: Path | None = None, config: Path | None = None, clock: Clock = local_now,
             power: PowerHistory | None = None, timestamper: Timestamper | None = None, desktop: Desktop | None = None) -> App:
    folder = DataFolder(data or data_folder.default_location())
    power = power or PowerJournal()
    timestamper = timestamper or Rfc3161Timestamper(folder.timestamps)
    config = config or place_book.default_location()
    places = PlaceBook(config, GitRemotes(folder.directory), GitFolders(folder.directory.parent / "chronata-places"))
    history = OptionalHistory(folder.directory, data_folder.LEDGER, lambda: any(p.kind == "git" for p in places.places()))
    sheet = Timesheet(LedgerFile(folder.ledger), history, WorkingDayFile(folder.working_day), power, write_lock(folder.lock), clock)

    def readable_copy(current: Timesheet, now: datetime) -> dict[str, bytes]:
        return readable_files(current.shifts(), current.weeks(), current.pc_sessions(), timestamper.stamps(), current.entry_count(), now)

    saving = Saving(places, timestamper, history, folder.sealed_files, readable_copy, folder.keep_readable)
    sheet.publish = saving
    return App(sheet, saving, history, timestamper, desktop or LinuxDesktop(), power)


def open_saved_copy(folder: Path) -> tuple[LedgerFile, Rfc3161Timestamper]:
    sealed = find_saved_copy(folder)
    return LedgerFile(sealed / data_folder.LEDGER), Rfc3161Timestamper(sealed / data_folder.TIMESTAMPS)
