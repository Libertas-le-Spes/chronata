import secrets
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

AUTHORITIES = {
    "digicert": "http://timestamp.digicert.com",
    "freetsa": "https://freetsa.org/tsr",
}
AUTHORITY_NAMES = {"digicert": "DigiCert", "freetsa": "FreeTSA"}
OWN_ROOTS = Path(__file__).parent / "authorities"
SYSTEM_ROOTS = [Path("/etc/ssl/certs/ca-certificates.crt"), Path("/etc/ssl/cert.pem"), Path("/etc/pki/tls/certs/ca-bundle.crt")]
SHA256 = bytes.fromhex("0609608648016503040201")
FOLDER = "timestamps"


@dataclass(frozen=True)
class Stamp:
    seq: int
    authority: str
    time: datetime
    path: Path

    @property
    def authority_name(self) -> str:
        return AUTHORITY_NAMES.get(self.authority, self.authority)


def stamp_head(directory: Path, seq: int, record_hash: str) -> tuple[list[Stamp], list[str]]:
    folder = directory / FOLDER
    folder.mkdir(exist_ok=True)
    have = {(s.seq, s.authority) for s in stamps(directory)}
    made, failures = [], []
    for authority, url in AUTHORITIES.items():
        if (seq, authority) in have:
            continue
        try:
            reply = _ask(url, bytes.fromhex(record_hash))
            when = _granted_time(reply, bytes.fromhex(record_hash))
        except (OSError, ValueError) as error:
            failures.append(f"{authority}: {error}")
            continue
        path = folder / f"{seq:06d}-{record_hash[:12]}-{authority}.tsr"
        path.write_bytes(reply)
        made.append(Stamp(seq, authority, when, path))
    return made, failures


def stamps(directory: Path) -> list[Stamp]:
    found = []
    for path in sorted((directory / FOLDER).glob("*.tsr")):
        seq, _, authority = path.stem.split("-", 2)
        try:
            when = _granted_time(path.read_bytes(), None)
        except ValueError:
            continue
        found.append(Stamp(int(seq), authority, when, path))
    return found


def check(stamp: Stamp, record_hash: str) -> str | None:
    reply = stamp.path.read_bytes()
    try:
        _granted_time(reply, bytes.fromhex(record_hash))
    except ValueError as error:
        return f"{stamp.path.name}: {error}"
    if shutil.which("openssl") is None:
        return None
    with tempfile.NamedTemporaryFile("wb", suffix=".pem") as roots:
        for source in [*filter(Path.exists, SYSTEM_ROOTS), *OWN_ROOTS.glob("*.pem")]:
            roots.write(source.read_bytes() + b"\n")
        roots.flush()
        verified = subprocess.run(
            ["openssl", "ts", "-verify", "-digest", record_hash, "-in", str(stamp.path), "-CAfile", roots.name],
            capture_output=True, text=True, check=False,
        )
    if "Verification: OK" not in verified.stdout:
        return f"{stamp.path.name}: signature does not verify ({verified.stderr.strip().splitlines()[-1:] or 'unknown error'})"
    return None


def _ask(url: str, digest: bytes) -> bytes:
    query = _tlv(0x30, b"".join([
        _tlv(0x02, b"\x01"),
        _tlv(0x30, _tlv(0x30, SHA256 + b"\x05\x00") + _tlv(0x04, digest)),
        _tlv(0x02, _integer(secrets.randbits(63))),
        _tlv(0x01, b"\xff"),
    ]))
    request = urllib.request.Request(url, data=query, headers={"Content-Type": "application/timestamp-query"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read()


def _granted_time(reply: bytes, digest: bytes | None) -> datetime:
    tag, body, _ = _read(reply, 0)
    status_tag, status, _ = _read(body, 0)
    _, code, _ = _read(status, 0)
    if tag != 0x30 or status_tag != 0x30 or int.from_bytes(code, "big") not in (0, 1):
        raise ValueError("the timestamp authority refused the request")
    info = _find_token_info(reply)
    if info is None:
        raise ValueError("the reply holds no timestamp")
    imprint, generated = info
    if digest is not None and imprint != digest:
        raise ValueError("the timestamp is for a different entry")
    return datetime.strptime(generated.decode().rstrip("Z").split(".")[0], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def _find_token_info(data: bytes) -> tuple[bytes, bytes] | None:
    for tag, body in _walk(data):
        if tag != 0x30:
            continue
        children = _children(body)
        if (len(children) >= 5 and children[0][0] == 0x02 and children[1][0] == 0x06
                and children[2][0] == 0x30 and children[4][0] == 0x18):
            imprint = _children(children[2][1])
            if len(imprint) == 2 and imprint[1][0] == 0x04:
                return imprint[1][1], children[4][1]
    return None


def _walk(data: bytes):
    for tag, body in _children(data):
        yield tag, body
        if tag & 0x20 or tag == 0x04:
            yield from _walk(body)


def _children(data: bytes) -> list[tuple[int, bytes]]:
    found, offset = [], 0
    try:
        while offset < len(data):
            tag, body, offset = _read(data, offset)
            found.append((tag, body))
    except ValueError:
        return []
    return found


def _read(data: bytes, offset: int) -> tuple[int, bytes, int]:
    if offset + 2 > len(data):
        raise ValueError("truncated")
    tag, length, offset = data[offset], data[offset + 1], offset + 2
    if length & 0x80:
        count = length & 0x7F
        if count == 0 or count > 4 or offset + count > len(data):
            raise ValueError("bad length")
        length, offset = int.from_bytes(data[offset:offset + count], "big"), offset + count
    if offset + length > len(data):
        raise ValueError("truncated")
    return tag, data[offset:offset + length], offset + length


def _integer(value: int) -> bytes:
    return value.to_bytes(value.bit_length() // 8 + 1, "big")


def _tlv(tag: int, body: bytes) -> bytes:
    if len(body) < 0x80:
        return bytes([tag, len(body)]) + body
    size = len(body).to_bytes((len(body).bit_length() + 7) // 8, "big")
    return bytes([tag, 0x80 | len(size)]) + size + body
