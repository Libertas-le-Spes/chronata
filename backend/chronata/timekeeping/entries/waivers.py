from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from chronata.timekeeping.entries.wording import detail, quoted
from chronata.timekeeping.record.record import Entry
from chronata.timekeeping.shifts.shifts import WAIVED, Break, Happening, Shift


@dataclass(frozen=True)
class TimeWaived:
    kind: ClassVar[str] = "time_waived"
    shift: int
    start: datetime
    end: datetime
    reason: str

    def data(self) -> dict:
        return {"shift": self.shift, "start": self.start.isoformat(), "end": self.end.isoformat(), "reason": self.reason}

    @staticmethod
    def apply(found: dict[int, Shift], entry: Entry) -> None:
        data = entry.data
        gap = Break(datetime.fromisoformat(data["start"]), datetime.fromisoformat(data["end"]), WAIVED, data["reason"])
        shift = found[data["shift"]]
        shift.add_break(gap)
        span = f"{gap.start:%H:%M:%S} – {gap.end:%H:%M:%S}"
        shift.changes.append(f"{entry.recorded_at:%Y-%m-%d %H:%M} waived {span}, not counted as work: {gap.reason}")
        shift.happenings.append(Happening(gap.start, "Waived", detail(span, "not counted", quoted(gap.reason))))


@dataclass(frozen=True)
class WaiverWithdrawn:
    kind: ClassVar[str] = "waiver_withdrawn"
    shift: int
    start: datetime
    reason: str

    def data(self) -> dict:
        return {"shift": self.shift, "start": self.start.isoformat(), "reason": self.reason}

    @staticmethod
    def apply(found: dict[int, Shift], entry: Entry) -> None:
        data = entry.data
        shift = found[data["shift"]]
        gap = shift.waived_from(datetime.fromisoformat(data["start"]))
        if gap is None:
            return
        shift.breaks.remove(gap)
        span = f"{gap.start:%H:%M:%S} – {gap.end:%H:%M:%S}"
        shift.changes.append(f"{entry.recorded_at:%Y-%m-%d %H:%M} took back the waiver for {span}: {data['reason']}")
        shift.happenings.append(Happening(gap.start, "Waiver taken back", detail(span, "counted again", quoted(data["reason"]))))
