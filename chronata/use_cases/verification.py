from dataclasses import dataclass

from chronata.timekeeping.stamps import Stamp, latest
from chronata.use_cases.ports import History, RecordStore, Timestamper


@dataclass(frozen=True)
class Findings:
    entries: int
    problems: list[str]
    stamps: list[Stamp]

    @property
    def latest_stamped(self) -> int | None:
        return latest(self.stamps)[0]


def verify(record: RecordStore, timestamper: Timestamper, history: History | None = None) -> Findings:
    problems = record.problems()
    stamps = timestamper.stamps()
    for stamp in stamps:
        expected = record.hash_of(stamp.seq)
        if expected is None:
            problems.append(f"{stamp.name}: timestamps entry {stamp.seq}, which is missing from the log")
            continue
        failure = timestamper.check(stamp, expected)
        if failure:
            problems.append(failure)
    if history is not None:
        problems += history.rewrites()
    return Findings(len(record.entries()), problems, stamps)
