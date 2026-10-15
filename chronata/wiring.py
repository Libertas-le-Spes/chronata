from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from chronata.adapters import locations, this_machine
from chronata.adapters.files import data_folder
from chronata.adapters.files.data_folder import DataFolder, find_saved_copy
from chronata.adapters.files.ledger_file import LedgerFile
from chronata.adapters.files.working_day_file import WorkingDayFile
from chronata.adapters.files.write_lock import write_lock
from chronata.adapters.history.optional_history import OptionalHistory
from chronata.adapters.places.git_folder import GitFolders
from chronata.adapters.places.git_push import GitRemotes
from chronata.adapters.places.place_book import PlaceBook
from chronata.adapters.places.save_record import SaveRecord
from chronata.adapters.timestamping.rfc3161 import Rfc3161Timestamper
from chronata.presenters.readable_copy import readable_files
from chronata.use_cases.ports import Clock, Desktop, History, PowerHistory, Timestamper
from chronata.use_cases.saving import Saving
from chronata.use_cases.clocking import Clocking
from chronata.use_cases.corrections import Corrections
from chronata.use_cases.labelling import Labelling
from chronata.use_cases.log import Log
from chronata.use_cases.payments import Payments
from chronata.use_cases.pc_records import PcRecords
from chronata.use_cases.working_day_setup import WorkingDaySetup


@dataclass(frozen=True)
class App:
    log: Log
    clocking: Clocking
    labels: Labelling
    corrections: Corrections
    pc: PcRecords
    payments: Payments
    setup: WorkingDaySetup
    saving: Saving
    history: History
    timestamper: Timestamper
    desktop: Desktop
    power: PowerHistory


def local_now() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


def open_app(data: Path | None = None, config: Path | None = None, clock: Clock = local_now,
             power: PowerHistory | None = None, timestamper: Timestamper | None = None, desktop: Desktop | None = None) -> App:
    folder = DataFolder(data or locations.log_folder())
    power = power or this_machine.power_history()
    timestamper = timestamper or Rfc3161Timestamper(folder.timestamps)
    settings = config or locations.settings_folder()
    save_record = SaveRecord(settings / "saves.json")
    places = PlaceBook(settings, GitRemotes(folder.directory), GitFolders(locations.repository_copies_folder(folder.directory)), save_record)
    history = OptionalHistory(folder.directory, data_folder.LEDGER, lambda: any(p.kind == "git" for p in places.places()))
    log = Log(LedgerFile(folder.ledger), history, WorkingDayFile(folder.working_day), write_lock(locations.lock_file(folder.directory)), clock)

    def readable_copy(current: Log, now: datetime) -> dict[str, bytes]:
        return readable_files(current.shifts(), current.weeks(), current.pc_sessions(), timestamper.stamps(), current.entry_count(), now)

    saving = Saving(places, save_record, timestamper, history, folder.sealed_files, readable_copy, folder.keep_readable)
    log.publish = saving
    labels = Labelling(log)
    pc = PcRecords(log, power)
    return App(log, Clocking(log, pc, labels), labels, Corrections(log, labels), pc, Payments(log), WorkingDaySetup(log, labels),
               saving, history, timestamper, desktop or this_machine.desktop(), power)


def open_saved_copy(folder: Path) -> tuple[LedgerFile, Rfc3161Timestamper]:
    sealed = find_saved_copy(folder)
    return LedgerFile(sealed / data_folder.LEDGER), Rfc3161Timestamper(sealed / data_folder.TIMESTAMPS)
