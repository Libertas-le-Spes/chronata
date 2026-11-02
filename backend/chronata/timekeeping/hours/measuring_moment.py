from dataclasses import dataclass
from datetime import datetime, time

from chronata.timekeeping.hours.clocked_day import ClockedDay
from chronata.timekeeping.hours.working_day import WorkingDay


@dataclass(frozen=True)
class MeasuringMoment:
    now: datetime | None
    clocked_in: bool

    def judged_at(self, clocked: ClockedDay, working_day: WorkingDay) -> time | None:
        if self.now is None or clocked.date != self.now.date():
            return None
        if self.clocked_in:
            return self.now.time()
        if self.now.time() < working_day.shift_end:
            return clocked.last_out.time()
        return None
