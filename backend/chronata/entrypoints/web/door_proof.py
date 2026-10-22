import hashlib
import hmac
import secrets

ASKED_BY_THE_DOOR = "door"
ANSWERED_BY_THE_PAGE = "page"


def fresh_nonce() -> str:
    return secrets.token_urlsafe(32)


def proof(key: str, *parts: str) -> str:
    return hmac.new(key.encode("utf-8"), "\n".join(parts).encode("utf-8"), hashlib.sha256).hexdigest()


def proves(key: str, given: str, *parts: str) -> bool:
    return hmac.compare_digest(given.encode("utf-8"), proof(key, *parts).encode("utf-8"))
