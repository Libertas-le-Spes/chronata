from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from chronata.timekeeping.record import Entry
from chronata.timekeeping.shifts import PC_OFF, Break, Shift


@dataclass(frozen=True)
class PowerSession:
    kind: ClassVar[str] = "pc_session"
    boot: str
    on: datetime
    off: datetime | None
    exact: bool = False

    def data(self) -> dict:
        data = {"boot": self.boot, "on": self.on.isoformat(), "off": self.off.isoformat() if self.off else None}
        return {**data, "exact": True} if self.exact else data


@dataclass(frozen=True)
class PcOffBreak:
    kind: ClassVar[str] = "pc_off_break"
    shift: int
    start: datetime
    end: datetime

    def data(self) -> dict:
        return {"shift": self.shift, "start": self.start.isoformat(), "end": self.end.isoformat()}

    @staticmethod
    def apply(found: dict[int, Shift], entry: Entry) -> None:
        gap = Break(datetime.fromisoformat(entry.data["start"]), datetime.fromisoformat(entry.data["end"]), PC_OFF)
        shift = found[entry.data["shift"]]
        shift.breaks.append(gap)
        shift.changes.append(f"PC off {gap.start:%H:%M:%S}–{gap.end:%H:%M:%S}, not counted as work")
