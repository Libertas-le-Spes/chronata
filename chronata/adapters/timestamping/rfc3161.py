import secrets
import shutil
import subprocess
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from chronata.adapters.timestamping import der
from chronata.timekeeping.stamps import Stamp

AUTHORITIES = {
    "digicert": ("DigiCert", "http://timestamp.digicert.com"),
    "freetsa": ("FreeTSA", "https://freetsa.org/tsr"),
}
OWN_ROOTS = Path(__file__).parent / "authorities"
SYSTEM_ROOTS = [Path("/etc/ssl/certs/ca-certificates.crt"), Path("/etc/ssl/cert.pem"), Path("/etc/pki/tls/certs/ca-bundle.crt")]
SHA256 = bytes.fromhex("0609608648016503040201")


class Rfc3161Timestamper:
    def __init__(self, folder: Path):
        self.folder = folder

    def stamp(self, seq: int, record_hash: str) -> tuple[list[Stamp], list[str]]:
        self.folder.mkdir(parents=True, exist_ok=True)
        have = {(s.seq, s.authority) for s in self.stamps()}
        made, failures = [], []
        for authority, (shown_name, url) in AUTHORITIES.items():
            if (seq, authority) in have:
                continue
            try:
                reply = _ask(url, bytes.fromhex(record_hash))
                when = _granted_time(reply, bytes.fromhex(record_hash))
            except (OSError, ValueError) as error:
                failures.append(f"{shown_name}: {error}")
                continue
            name = f"{seq:06d}-{record_hash[:12]}-{authority}.tsr"
            (self.folder / name).write_bytes(reply)
            made.append(Stamp(seq, authority, shown_name, when, name))
        return made, failures

    def stamps(self) -> list[Stamp]:
        found = []
        for path in sorted(self.folder.glob("*.tsr")):
            seq, _, authority = path.stem.split("-", 2)
            try:
                when = _granted_time(path.read_bytes(), None)
            except ValueError:
                continue
            found.append(Stamp(int(seq), authority, AUTHORITIES.get(authority, (authority, ""))[0], when, path.name))
        return found

    def check(self, stamp: Stamp, record_hash: str) -> str | None:
        path = self.folder / stamp.name
        try:
            _granted_time(path.read_bytes(), bytes.fromhex(record_hash))
        except ValueError as error:
            return f"{stamp.name}: {error}"
        if shutil.which("openssl") is None:
            return None
        with tempfile.NamedTemporaryFile("wb", suffix=".pem") as roots:
            for source in [*filter(Path.exists, SYSTEM_ROOTS), *OWN_ROOTS.glob("*.pem")]:
                roots.write(source.read_bytes() + b"\n")
            roots.flush()
            verified = subprocess.run(
                ["openssl", "ts", "-verify", "-digest", record_hash, "-in", str(path), "-CAfile", roots.name],
                capture_output=True, text=True, check=False,
            )
        if "Verification: OK" not in verified.stdout:
            return f"{stamp.name}: signature does not verify ({verified.stderr.strip().splitlines()[-1:] or 'unknown error'})"
        return None


def _ask(url: str, digest: bytes) -> bytes:
    query = der.tlv(0x30, b"".join([
        der.tlv(0x02, b"\x01"),
        der.tlv(0x30, der.tlv(0x30, SHA256 + b"\x05\x00") + der.tlv(0x04, digest)),
        der.tlv(0x02, der.integer(secrets.randbits(63))),
        der.tlv(0x01, b"\xff"),
    ]))
    request = urllib.request.Request(url, data=query, headers={"Content-Type": "application/timestamp-query"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read()


def _granted_time(reply: bytes, digest: bytes | None) -> datetime:
    if not _granted(reply):
        raise ValueError("the timestamp authority refused the request")
    info = _find_token_info(reply)
    if info is None:
        raise ValueError("the reply holds no timestamp")
    imprint, generated = info
    if digest is not None and imprint != digest:
        raise ValueError("the timestamp is for a different entry")
    return datetime.strptime(generated.decode().rstrip("Z").split(".")[0], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def _find_token_info(data: bytes) -> tuple[bytes, bytes] | None:
    for tag, body in der.walk(data):
        if tag != 0x30:
            continue
        children = der.children(body)
        if not _shaped_like_token_info(children):
            continue
        imprint = der.children(children[2][1])
        if len(imprint) == 2 and imprint[1][0] == 0x04:
            return imprint[1][1], children[4][1]
    return None


def _granted(reply: bytes) -> bool:
    tag, body, _ = der.read(reply, 0)
    status_tag, status, _ = der.read(body, 0)
    _, code, _ = der.read(status, 0)
    if (tag, status_tag) != (0x30, 0x30):
        return False
    return int.from_bytes(code, "big") in (0, 1)


def _shaped_like_token_info(children: list[tuple[int, bytes]]) -> bool:
    expected = (0x02, 0x06, 0x30, None, 0x18)
    if len(children) < len(expected):
        return False
    return all(tag is None or children[at][0] == tag for at, tag in enumerate(expected))
