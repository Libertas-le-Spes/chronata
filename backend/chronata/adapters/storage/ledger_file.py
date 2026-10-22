import json
from datetime import datetime
from pathlib import Path

from chronata.adapters.storage.owner_only_file import append_owner_only
from chronata.timekeeping.record.record import Entry, GENESIS, TamperedRecord, chain_problems, entry_of, sealed


class LedgerFile:
    def __init__(self, path: Path):
        self.path = path

    def entries(self) -> list[Entry]:
        return [entry_of(record) for record in self._records()]

    def append(self, kind: str, data: dict, now: datetime) -> Entry:
        records = self._records()
        problems = self.problems()
        if problems:
            raise TamperedRecord("\n".join(problems))
        record = sealed(len(records) + 1, kind, data, now, records[-1]["hash"] if records else GENESIS)
        append_owner_only(self.path, (json.dumps(record, sort_keys=True) + "\n").encode("utf-8"))
        return entry_of(record)

    def head(self) -> tuple[int, str] | None:
        records = self._records()
        return (records[-1]["seq"], records[-1]["hash"]) if records else None

    def hash_of(self, seq: int) -> str | None:
        records = self._records()
        return records[seq - 1]["hash"] if 0 < seq <= len(records) else None

    def problems(self) -> list[str]:
        unreadable = [f"line {number}: is not a whole entry; if it is the last line, it was being written when "
                      f"the PC stopped and can be removed by hand from {self.path}" for number, raw in self._lines() if _parsed(raw) is None]
        return unreadable + chain_problems(self._records())

    def _records(self) -> list[dict]:
        return [record for record in (_parsed(raw) for _, raw in self._lines()) if record is not None]

    def _lines(self) -> list[tuple[int, str]]:
        if not self.path.exists():
            return []
        text = self.path.read_bytes().decode("utf-8", errors="replace")
        return [(number, line) for number, line in enumerate(text.splitlines(), 1) if line.strip()]


def _parsed(raw: str) -> dict | None:
    try:
        record = json.loads(raw)
    except ValueError:
        return None
    return record if isinstance(record, dict) and _readable_entry(record) else None


def _readable_entry(record: dict) -> bool:
    try:
        entry_of(record)
    except (KeyError, TypeError, ValueError):
        return False
    return isinstance(record.get("data"), dict)
