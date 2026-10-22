import hashlib
import json
import re
import secrets
import urllib.request
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Callable

from chronata.adapters.storage.owner_only_file import make_owner_only_folder, write_owner_only
from chronata.adapters.timestamping import der
from chronata.adapters.timestamping.authority import AUTHORITIES, Authority
from chronata.adapters.timestamping.receipt_check import ReceiptRefused, checked_receipt, checked_reply
from chronata.timekeeping.record.stamps import Stamp
from chronata.use_cases.log.ports import CannotCheck

SHA256 = bytes.fromhex("0609608648016503040201")
RECEIPT_NAME = re.compile(r"^(\d{6})-([0-9a-f]{12})-([a-z]+)\.tsr$")
LARGEST_REPLY = 64 * 1024
ASK_SECONDS = 10

HashOf = Callable[[int], str | None]
Ask = Callable[[str, bytes], bytes]


class Rfc3161Timestamper:
    def __init__(self, folder: Path, hash_of: HashOf, checked: Path | None = None, ask: Ask | None = None,
                 authorities: tuple[Authority, ...] = AUTHORITIES):
        self.folder = folder
        self.hash_of = hash_of
        self.checked = checked
        self.ask = ask or _ask
        self.by_id = {authority.id: authority for authority in authorities}

    def stamp(self, seq: int, record_hash: str) -> tuple[list[Stamp], list[str]]:
        make_owner_only_folder(self.folder)
        have = {stamp.name for stamp in self.stamps()}
        made, failures = [], []
        for authority in self.by_id.values():
            name = _receipt_name(seq, record_hash, authority)
            if name in have:
                continue
            query = _query(record_hash)
            try:
                reply = self.ask(authority.url, query)
                when = checked_reply(reply, query, authority)
            except (OSError, ReceiptRefused, CannotCheck) as error:
                failures.append(f"{authority.name}: {error}")
                continue
            write_owner_only(self.folder / name, reply)
            self._remember(name, reply, record_hash, when)
            made.append(Stamp(seq, authority.id, authority.name, when, name))
        return made, failures

    def stamps(self) -> list[Stamp]:
        found = []
        for path, seq, authority in self._receipts():
            record_hash = self.hash_of(seq)
            if authority is None or record_hash is None or not path.name.startswith(f"{seq:06d}-{record_hash[:12]}-"):
                continue
            when = self._checked_time(path, record_hash, authority)
            if when is not None:
                found.append(Stamp(seq, authority.id, authority.name, when, path.name))
        return found

    def problems(self) -> list[str]:
        problems = []
        for path, seq, authority in self._receipts():
            problem = self._problem_with(path, seq, authority)
            if problem:
                problems.append(f"{path.name}: {problem}")
        return problems

    def _problem_with(self, path: Path, seq: int, authority: Authority | None) -> str | None:
        record_hash = self.hash_of(seq)
        if authority is None:
            return "is not from a timestamp authority Chronata uses"
        if record_hash is None:
            return f"timestamps entry {seq}, which is missing from the log"
        if not path.name.startswith(f"{seq:06d}-{record_hash[:12]}-"):
            return f"timestamps a different version of entry {seq}; the log was changed or rolled back after it was timestamped"
        try:
            checked_receipt(path.read_bytes(), record_hash, authority)
        except ReceiptRefused as error:
            return str(error)
        return None

    def _receipts(self) -> list[tuple[Path, int, Authority | None]]:
        if not self.folder.is_dir():
            return []
        named = ((path, RECEIPT_NAME.match(path.name)) for path in sorted(self.folder.glob("*.tsr")))
        return [(path, int(match[1]), self.by_id.get(match[3])) for path, match in named if match]

    def _checked_time(self, path: Path, record_hash: str, authority: Authority) -> datetime | None:
        reply = path.read_bytes()
        remembered = self._remembered().get(path.name, {})
        if isinstance(remembered, dict) and remembered.get("receipt") == _digest(reply) and remembered.get("entry") == record_hash:
            with suppress(TypeError, ValueError):
                return datetime.fromisoformat(remembered["time"])
        try:
            when = checked_receipt(reply, record_hash, authority)
        except (ReceiptRefused, CannotCheck):
            return None
        self._remember(path.name, reply, record_hash, when)
        return when

    def _remember(self, name: str, reply: bytes, record_hash: str, when: datetime) -> None:
        if self.checked is None:
            return
        remembered = {**self._remembered(), name: {"receipt": _digest(reply), "entry": record_hash, "time": when.isoformat()}}
        write_owner_only(self.checked, (json.dumps(remembered, indent=2) + "\n").encode("utf-8"))

    def _remembered(self) -> dict:
        if self.checked is None or not self.checked.exists():
            return {}
        try:
            remembered = json.loads(self.checked.read_text(encoding="utf-8"))
        except ValueError:
            return {}
        return remembered if isinstance(remembered, dict) else {}


def _receipt_name(seq: int, record_hash: str, authority: Authority) -> str:
    return f"{seq:06d}-{record_hash[:12]}-{authority.id}.tsr"


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _query(record_hash: str) -> bytes:
    return der.tlv(0x30, b"".join([
        der.tlv(0x02, b"\x01"),
        der.tlv(0x30, der.tlv(0x30, SHA256 + b"\x05\x00") + der.tlv(0x04, bytes.fromhex(record_hash))),
        der.tlv(0x02, der.integer(secrets.randbits(63))),
        der.tlv(0x01, b"\xff"),
    ]))


def _ask(url: str, query: bytes) -> bytes:
    request = urllib.request.Request(url, data=query, headers={"Content-Type": "application/timestamp-query"})
    with urllib.request.urlopen(request, timeout=ASK_SECONDS) as response:
        reply = response.read(LARGEST_REPLY + 1)
    if len(reply) > LARGEST_REPLY:
        raise ReceiptRefused("the reply was far larger than a receipt")
    return reply
