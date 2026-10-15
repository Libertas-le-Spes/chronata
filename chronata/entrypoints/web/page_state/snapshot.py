from dataclasses import dataclass
from datetime import datetime

from chronata.timekeeping.pc_sessions import PcSession
from chronata.timekeeping.shifts import Shift, open_shift
from chronata.timekeeping.label_hours import LabelHours
from chronata.timekeeping.overtime import Week
from chronata.use_cases.pc_records import Interrupted


@dataclass(frozen=True)
class Snapshot:
    now: datetime
    hours: LabelHours
    shifts: list[Shift]
    weeks: list[Week]
    sessions: list[PcSession]
    current: Shift | None
    interrupted: Interrupted | None

    @classmethod
    def of(cls, app) -> "Snapshot":
        all_shifts = app.log.shifts()
        return cls(app.log.clock(), app.log.hours, all_shifts, app.log.weeks(), app.log.pc_sessions(),
                   open_shift(all_shifts), app.pc.interrupted())
