import os
import socket
import sys
from pathlib import Path

TCP_TABLE = Path("/proc/net/tcp")
ESTABLISHED = "01"
LISTENING = "0A"
ANYONE = "00000000:0000"


def owned_by_this_user(client: tuple[str, int], server: tuple[str, int]) -> bool:
    return connection_owner(client, server, _read(TCP_TABLE)) == os.getuid()


def listened_on_by_this_user(address: tuple[str, int]) -> bool:
    return listener_owner(address, _read(TCP_TABLE)) == os.getuid()


def listener_owner(address: tuple[str, int], table: str) -> int | None:
    return _owner_of_row(table, (_as_listed(address), ANYONE, LISTENING))


def connection_owner(client: tuple[str, int], server: tuple[str, int], table: str) -> int | None:
    return _owner_of_row(table, (_as_listed(client), _as_listed(server), ESTABLISHED))


def _owner_of_row(table: str, wanted: tuple[str, str, str]) -> int | None:
    for row in table.splitlines()[1:]:
        fields = row.split()
        if len(fields) > 7 and (fields[1], fields[2], fields[3]) == wanted:
            return int(fields[7])
    return None


def _as_listed(address: tuple[str, int]) -> str:
    host, port = address
    return f"{int.from_bytes(socket.inet_aton(host), sys.byteorder):08X}:{port:04X}"


def _read(table: Path) -> str:
    try:
        return table.read_text()
    except OSError:
        return ""
