from dataclasses import dataclass
from datetime import datetime

from chronata.timekeeping.compensation.reconciliation import Reconciliation
from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.week import Week
from chronata.timekeeping.pc.pc_sessions import PcSession
from chronata.timekeeping.record.stamps import Stamp
from chronata.timekeeping.shifts.shifts import Shift
from chronata.use_cases.log.ports import Place, PlaceKindDescription
from chronata.use_cases.pc.pc_records import Interrupted
from chronata.use_cases.reminders.reminder_pace import ReminderPace


@dataclass(frozen=True)
class PageFacts:
    now: datetime
    hours: LabelHours
    shifts: list[Shift]
    weeks: list[Week]
    sessions: list[PcSession]
    current: Shift | None
    interrupted: Interrupted | None
    this_boot: PcSession | None
    unclocked_since: datetime | None
    suggested_label: str
    stamps: list[Stamp]
    entry_count: int
    problems: list[str]
    compensation: dict[str, Reconciliation]
    places: list[tuple[Place, dict]]
    place_kinds: dict[str, PlaceKindDescription]
    newest_stamped: int | None
    stamped_by: list[Stamp]
    reminder_pace: ReminderPace = ReminderPace()
