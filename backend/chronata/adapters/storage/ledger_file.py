import json
from datetime import datetime
from pathlib import Path

from chronata.timekeeping.record.record import Entry, GENESIS, TamperedRecord, chain_problems, entry_of, sealed


class LedgerFile:
    def __init__(self, path: Path):
        self.path = path

    def entries(self) -> list[Entry]:
        return [entry_of(record) for record in self._records()]

    def append(self, kind: str, data: dict, now: datetime) -> Entry:
        records = self._records()
        problems = chain_problems(records)
        if problems:
            raise TamperedRecord("\n".join(problems))
        record = sealed(len(records) + 1, kind, data, now, records[-1]["hash"] if records else GENESIS)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, sort_keys=True) + "\n")
        return entry_of(record)

    def head(self) -> tuple[int, str] | None:
        records = self._records()
        return (records[-1]["seq"], records[-1]["hash"]) if records else None

    def hash_of(self, seq: int) -> str | None:
        records = self._records()
        return records[seq - 1]["hash"] if 0 < seq <= len(records) else None

    def problems(self) -> list[str]:
        return chain_problems(self._records())

    def _records(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
