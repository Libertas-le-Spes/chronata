import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

GENESIS = "0" * 64


@dataclass(frozen=True)
class Entry:
    seq: int
    kind: str
    recorded_at: datetime
    data: dict


class TamperedRecord(Exception):
    pass


def sealed(seq: int, kind: str, data: dict, now: datetime, previous_hash: str) -> dict:
    record = {"seq": seq, "kind": kind, "recorded_at": now.isoformat(), "data": data, "prev": previous_hash}
    return {**record, "hash": seal_of(record)}


def seal_of(record: dict) -> str:
    content = {key: value for key, value in record.items() if key != "hash"}
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def chain_problems(records: list[dict]) -> list[str]:
    problems = []
    previous = GENESIS
    for line, record in enumerate(records, start=1):
        if record.get("seq") != line:
            problems.append(f"line {line}: sequence number is {record.get('seq')}, a line was removed or reordered")
        if record.get("prev") != previous:
            problems.append(f"line {line}: does not follow on from the line before it")
        if record.get("hash") != seal_of(record):
            problems.append(f"line {line}: contents were changed after it was written")
        previous = record.get("hash")
    return problems


def entry_of(record: dict) -> Entry:
    return Entry(record["seq"], record["kind"], datetime.fromisoformat(record["recorded_at"]), record["data"])
