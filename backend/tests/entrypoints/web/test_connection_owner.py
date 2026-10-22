import os
import socket
import unittest
from pathlib import Path
from unittest import mock

from chronata.entrypoints.web import connection_owner
from chronata.entrypoints.web.connection_owner import connection_owner as owner_of, owned_by_this_user

HEADER = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
CLIENT_SIDE = "   1: 0100007F:D431 0100007F:BA2E 01 00000000:00000000 00:00000000 00000000  1234        0 111 1\n"
SERVER_SIDE = "   2: 0100007F:BA2E 0100007F:D431 01 00000000:00000000 00:00000000 00000000  1000        0 222 1\n"
CLOSING = "   3: 0100007F:D432 0100007F:BA2E 06 00000000:00000000 00:00000000 00000000  1234        0 333 1\n"

CLIENT = ("127.0.0.1", 0xD431)
SERVER = ("127.0.0.1", 0xBA2E)


class TheOwnerOfAConnection(unittest.TestCase):
    def test_is_read_from_the_clients_end(self):
        self.assertEqual(owner_of(CLIENT, SERVER, HEADER + SERVER_SIDE + CLIENT_SIDE), 1234)

    def test_is_not_taken_from_the_servers_own_end(self):
        self.assertIsNone(owner_of(CLIENT, SERVER, HEADER + SERVER_SIDE))

    def test_counts_only_open_connections(self):
        self.assertIsNone(owner_of(("127.0.0.1", 0xD432), SERVER, HEADER + CLOSING))

    def test_is_unknown_when_the_table_cannot_be_read(self):
        with mock.patch.object(connection_owner, "TCP_TABLE", Path("/nonexistent/tcp")):
            self.assertFalse(owned_by_this_user(CLIENT, SERVER))

    def test_of_a_real_connection_is_this_user(self):
        with socket.create_server(("127.0.0.1", 0)) as listening, socket.create_connection(listening.getsockname()) as client:
            accepted, _ = listening.accept()
            with accepted:
                self.assertTrue(owned_by_this_user(client.getsockname(), listening.getsockname()))
                self.assertEqual(owner_of(client.getsockname(), listening.getsockname(), connection_owner.TCP_TABLE.read_text()), os.getuid())


if __name__ == "__main__":
    unittest.main()
