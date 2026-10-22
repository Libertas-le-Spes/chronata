from dataclasses import dataclass

from chronata.timekeeping.record.stamps import Stamp, latest
from chronata.use_cases.log.ports import History, RecordStore, Timestamper


@dataclass(frozen=True)
class Findings:
    entries: int
    problems: list[str]
    stamps: list[Stamp]

    @property
    def latest_stamped(self) -> int | None:
        return latest(self.stamps)[0]


def verify(record: RecordStore, timestamper: Timestamper, history: History | None = None) -> Findings:
    problems = record.problems() + timestamper.problems()
    stamps = timestamper.stamps()
    if history is not None:
        problems += history.rewrites()
    return Findings(len(record.entries()), problems, stamps)
