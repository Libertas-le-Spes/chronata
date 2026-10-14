import base64
import hashlib
import urllib.error
import urllib.parse
import urllib.request

from chronata.use_cases.ports import SaveError


def upload_changed(address: str, username: str, password: str, bundle: dict[str, bytes], already_sent: dict[str, str]) -> dict[str, str]:
    base = address.rstrip("/") + "/Chronata/"
    sent = dict(already_sent)
    made_folders: set[str] = set()
    for relative, content in sorted(bundle.items()):
        digest = hashlib.sha256(content).hexdigest()
        if sent.get(relative) == digest:
            continue
        parts = relative.split("/")[:-1]
        for depth in range(len(parts) + 1):
            folder = "/".join(parts[:depth])
            if folder not in made_folders:
                _send(address, username, password, "MKCOL", base + _quoted(folder) + ("/" if folder else ""), None, accept=(201, 301, 405))
                made_folders.add(folder)
        _send(address, username, password, "PUT", base + _quoted(relative), content, accept=(200, 201, 204))
        sent[relative] = digest
    return sent


def _send(address: str, username: str, password: str, method: str, url: str, body: bytes | None, accept: tuple[int, ...]) -> None:
    request = urllib.request.Request(url, data=body, method=method)
    if username:
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        request.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
        error.close()
    except (urllib.error.URLError, OSError) as error:
        raise SaveError(f"could not reach {address}: {getattr(error, 'reason', error)}")
    if status in (401, 403):
        raise SaveError(f"{address} refused the username or password")
    if status not in accept:
        raise SaveError(f"{address} answered {status} to {method} {url}")


def _quoted(relative: str) -> str:
    return "/".join(urllib.parse.quote(part) for part in relative.split("/") if part)
