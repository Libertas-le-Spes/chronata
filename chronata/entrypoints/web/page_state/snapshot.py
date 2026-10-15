from dataclasses import dataclass
from datetime import datetime

from chronata.timekeeping.pc_sessions import PcSession
from chronata.timekeeping.shifts import Shift, open_shift
from chronata.timekeeping.working_day import Week, WorkingDay
from chronata.use_cases.pc_records import Interrupted


@dataclass(frozen=True)
class Snapshot:
    now: datetime
    working_day: WorkingDay
    shifts: list[Shift]
    weeks: list[Week]
    sessions: list[PcSession]
    current: Shift | None
    interrupted: Interrupted | None

    @classmethod
    def of(cls, app) -> "Snapshot":
        all_shifts = app.log.shifts()
        return cls(app.log.clock(), app.log.working_day, all_shifts, app.log.weeks(), app.log.pc_sessions(),
                   open_shift(all_shifts), app.pc.interrupted())
