import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from chronata.adapters.storage.owner_only_file import write_owner_only
from chronata.adapters.timestamping.authority import Authority
from chronata.use_cases.log.ports import CannotCheck

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
GRANTED_AT = re.compile(r"^Time stamp: (\w{3}) +(\d{1,2}) (\d\d):(\d\d):(\d\d)(?:\.\d+)? (\d{4}) GMT$", re.MULTILINE)
CHECK_SECONDS = 30


class ReceiptRefused(ValueError):
    pass


def checked_reply(reply: bytes, query: bytes, authority: Authority) -> datetime:
    return _checked(reply, authority, query=query)


def checked_receipt(reply: bytes, digest: str, authority: Authority) -> datetime:
    return _checked(reply, authority, digest=digest)


def _checked(reply: bytes, authority: Authority, query: bytes | None = None, digest: str | None = None) -> datetime:
    if shutil.which("openssl") is None:
        raise CannotCheck("openssl is not installed, so the timestamp receipts cannot be checked")
    with tempfile.TemporaryDirectory() as scratch:
        receipt = Path(scratch) / "receipt.tsr"
        write_owner_only(receipt, reply)
        against = ["-digest", digest] if digest else ["-queryfile", _written(Path(scratch) / "query.tsq", query)]
        verified = _openssl("ts", "-verify", *against, "-in", str(receipt), "-CAfile", str(authority.anchor))
        if "Verification: OK" not in verified.stdout:
            reason = (verified.stderr.strip().splitlines() or ["unknown error"])[-1]
            raise ReceiptRefused(f"it is not a genuine {authority.name} receipt for this entry ({reason})")
        return _granted_at(_openssl("ts", "-reply", "-in", str(receipt), "-text").stdout)


def _written(path: Path, content: bytes) -> str:
    write_owner_only(path, content)
    return str(path)


def _openssl(*args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["openssl", *args], capture_output=True, text=True, check=False, timeout=CHECK_SECONDS)
    except subprocess.TimeoutExpired:
        raise ReceiptRefused("openssl took too long to check it")


def _granted_at(text: str) -> datetime:
    found = GRANTED_AT.search(text)
    if found is None or found[1] not in MONTHS:
        raise ReceiptRefused("it holds no time")
    month, day, hour, minute, second, year = MONTHS.index(found[1]) + 1, *map(int, found.groups()[1:])
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
