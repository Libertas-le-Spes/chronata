from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from chronata.adapters import this_machine
from chronata.adapters.history.optional_history import OptionalHistory
from chronata.adapters.places.kinds.folder_place import FolderPlace, ObsidianVault
from chronata.adapters.places.kinds.git_folder_place import GitRepositoryFolder
from chronata.adapters.places.kinds.git_place import GitRepository
from chronata.adapters.places.kinds.webdav_place import WebDavServer
from chronata.adapters.places.place_book import PlaceBook
from chronata.adapters.places.save_record import SaveRecord
from chronata.adapters.places.transport.git_folder import GitFolders
from chronata.adapters.places.transport.git_push import GitRemotes
from chronata.adapters.places.transport.git_transport import GitTransport
from chronata.adapters.secrets.secret_service import SecretService
from chronata.adapters.storage import data_folder, locations
from chronata.adapters.storage.data_folder import DataFolder, find_saved_copy
from chronata.adapters.storage.label_hours_file import LabelHoursFile
from chronata.adapters.storage.ledger_file import LedgerFile
from chronata.adapters.storage.owner_only_folder import OwnerOnlyFolder
from chronata.adapters.storage.write_lock import write_lock
from chronata.adapters.timestamping.rfc3161 import Rfc3161Timestamper
from chronata.presenters.readable_copy.readable_copy import readable_files
from chronata.use_cases.clocking.clocking import Clocking
from chronata.use_cases.compensation.compensations import Compensations
from chronata.use_cases.corrections.corrections import Corrections
from chronata.use_cases.hours.working_day_setup import WorkingDaySetup
from chronata.use_cases.labels.labelling import Labelling
from chronata.use_cases.log.log import Log
from chronata.use_cases.log.ports import Clock, Desktop, History, PowerHistory, Secrets, Timestamper
from chronata.use_cases.pc.pc_records import PcRecords
from chronata.use_cases.saving.saving import Saving


@dataclass(frozen=True)
class App:
    log: Log
    clocking: Clocking
    labels: Labelling
    corrections: Corrections
    pc: PcRecords
    compensations: Compensations
    setup: WorkingDaySetup
    saving: Saving
    history: History
    timestamper: Timestamper
    desktop: Desktop
    power: PowerHistory
    web_page: Path
    running: OwnerOnlyFolder


def local_now() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


def open_app(data: Path | None = None, config: Path | None = None, clock: Clock = local_now,
             power: PowerHistory | None = None, timestamper: Timestamper | None = None, desktop: Desktop | None = None,
             secrets: Secrets | None = None, git: GitTransport | None = None) -> App:
    folder = DataFolder(data or locations.log_folder())
    power = power or this_machine.power_history()
    settings = config or locations.settings_folder()
    save_record = SaveRecord(settings / "saves.json")
    git = git or GitTransport()
    kinds = [ObsidianVault(save_record), FolderPlace(save_record), GitRepository(GitRemotes(folder.directory, git)),
             GitRepositoryFolder(GitFolders(locations.repository_copies_folder(folder.directory), save_record, git)),
             WebDavServer(save_record, secrets or SecretService())]
    places = PlaceBook(settings, kinds)
    history = OptionalHistory(folder.directory, data_folder.LEDGER, places.needs_local_history)
    running = OwnerOnlyFolder(locations.runtime_folder())
    ledger = LedgerFile(folder.ledger)
    timestamper = timestamper or Rfc3161Timestamper(folder.timestamps, ledger.hash_of, folder.directory / data_folder.CHECKED_RECEIPTS)
    log = Log(ledger, history, LabelHoursFile(folder.rules), write_lock(running, locations.lock_name(folder.directory)), clock)

    def readable_copy(current: Log, now: datetime) -> dict[str, bytes]:
        return readable_files(current.shifts(), current.hours, current.pc_sessions(), timestamper.stamps(), current.entry_count(), now)

    saving = Saving(places, save_record, timestamper, history, folder.sealed_files, readable_copy, folder.keep_readable)
    log.publish = saving
    labels = Labelling(log)
    pc = PcRecords(log, power)
    return App(log, Clocking(log, pc, labels), labels, Corrections(log, labels), pc, Compensations(log, labels), WorkingDaySetup(log, labels),
               saving, history, timestamper, desktop or this_machine.desktop(), power, locations.web_page_folder(), running)


def open_saved_copy(folder: Path) -> tuple[LedgerFile, Rfc3161Timestamper]:
    sealed = find_saved_copy(folder)
    ledger = LedgerFile(sealed / data_folder.LEDGER)
    return ledger, Rfc3161Timestamper(sealed / data_folder.TIMESTAMPS, ledger.hash_of)
