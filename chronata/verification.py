from dataclasses import dataclass
from pathlib import Path

from chronata import timestamps
from chronata.ledger import Ledger
from chronata.timestamps import Stamp


@dataclass(frozen=True)
class Findings:
    entries: int
    problems: list[str]
    stamps: list[Stamp]

    @property
    def latest_stamped(self) -> int | None:
        return max((s.seq for s in self.stamps), default=None)


def check(ledger: Ledger, stamps_home: Path) -> Findings:
    problems = ledger.verify()
    stamps = timestamps.stamps(stamps_home)
    for stamp in stamps:
        expected = ledger.hash_of(stamp.seq)
        if expected is None:
            problems.append(f"{stamp.path.name}: timestamps entry {stamp.seq}, which is missing from the log")
            continue
        failure = timestamps.check(stamp, expected)
        if failure:
            problems.append(failure)
    return Findings(len(ledger.entries()), problems, stamps)


def sealed_folder(folder: Path) -> Path:
    for candidate in (folder, folder / "sealed", folder / "Chronata" / "sealed"):
        if (candidate / "ledger.jsonl").exists():
            return candidate
    raise FileNotFoundError(f"no Chronata log found in {folder}")
