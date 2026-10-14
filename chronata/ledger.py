import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

GENESIS = "0" * 64


@dataclass(frozen=True)
class Entry:
    seq: int
    kind: str
    recorded_at: datetime
    data: dict


class TamperedLedger(Exception):
    pass


class Ledger:
    def __init__(self, path: Path):
        self.path = path

    def entries(self) -> list[Entry]:
        return [_entry(record) for record in self._records()]

    def append(self, kind: str, data: dict, now: datetime) -> Entry:
        problems = self.verify()
        if problems:
            raise TamperedLedger("\n".join(problems))
        records = self._records()
        record = {
            "seq": len(records) + 1,
            "kind": kind,
            "recorded_at": now.isoformat(),
            "data": data,
            "prev": records[-1]["hash"] if records else GENESIS,
        }
        record["hash"] = _digest(record)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, sort_keys=True) + "\n")
        return _entry(record)

    def head(self) -> tuple[int, str] | None:
        records = self._records()
        return (records[-1]["seq"], records[-1]["hash"]) if records else None

    def hash_of(self, seq: int) -> str | None:
        records = self._records()
        return records[seq - 1]["hash"] if 0 < seq <= len(records) else None

    def verify(self) -> list[str]:
        problems = []
        prev = GENESIS
        for line_number, record in enumerate(self._records(), start=1):
            if record.get("seq") != line_number:
                problems.append(f"line {line_number}: sequence number is {record.get('seq')}, a line was removed or reordered")
            if record.get("prev") != prev:
                problems.append(f"line {line_number}: does not follow on from the line before it")
            if record.get("hash") != _digest(record):
                problems.append(f"line {line_number}: contents were changed after it was written")
            prev = record.get("hash")
        return problems

    def _records(self) -> list[dict]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]


def _digest(record: dict) -> str:
    sealed = {key: value for key, value in record.items() if key != "hash"}
    canonical = json.dumps(sealed, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _entry(record: dict) -> Entry:
    return Entry(record["seq"], record["kind"], datetime.fromisoformat(record["recorded_at"]), record["data"])
