import re
from urllib.parse import urlsplit

from chronata.use_cases.log.ports import SaveError

SCP_STYLE = re.compile(r"^([A-Za-z0-9._-]+@)?[A-Za-z0-9][A-Za-z0-9.-]*:(?![-:]|//)\S+$")
UNENCRYPTED = ("http", "git")
UNSAFE_TEXT = re.compile(r"[\s\x00-\x1f\x7f]")
CREDENTIALS = re.compile(r"(?<=//)[^/@\s]*@")


def checked_web_address(text: str) -> str:
    address = _bare(text)
    parts = urlsplit(address)
    if parts.scheme != "https" or not parts.hostname:
        raise SaveError("a web server address starts with https://, so the password never crosses the network unencrypted")
    _refuse_credentials(parts)
    return address


def checked_git_address(text: str) -> str:
    address = _bare(text)
    if address.startswith("/") or SCP_STYLE.match(address):
        return address
    parts = urlsplit(address)
    if parts.scheme in UNENCRYPTED:
        raise SaveError(f"{parts.scheme}:// sends the log unencrypted and unauthenticated; use https:// or ssh instead")
    if parts.scheme == "file" and parts.path.startswith("/"):
        return address
    if parts.scheme not in ("https", "ssh") or not parts.hostname:
        raise SaveError("give the repository as an https:// or ssh:// address, as host:path, or as a folder on this computer")
    if parts.scheme == "https":
        _refuse_credentials(parts)
    elif parts.password:
        raise SaveError("leave the password out of the address; ssh keys or git's credential helper keep it")
    return address


def shown(address: str) -> str:
    return CREDENTIALS.sub("", address)


def _bare(text: str) -> str:
    address = text.strip()
    if not address or address.startswith("-") or UNSAFE_TEXT.search(address):
        raise SaveError("that address has spaces, control characters or starts with '-', so it was refused")
    return address


def _refuse_credentials(parts) -> None:
    if parts.username or parts.password:
        raise SaveError("leave the name and password out of the address; Chronata keeps them in the desktop keyring or git's credential helper")
