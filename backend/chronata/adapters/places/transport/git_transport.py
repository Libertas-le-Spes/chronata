from chronata.adapters.places.addresses import checked_git_address

SAFE_TRANSPORTS = ("-c", "protocol.allow=never", "-c", "protocol.https.allow=always", "-c", "protocol.ssh.allow=always",
                   "-c", "core.hooksPath=/dev/null")
LOCAL_TRANSPORT = ("-c", "protocol.file.allow=always")


class GitTransport:
    def __init__(self, local_allowed: bool = False):
        self.local_allowed = local_allowed

    def checked(self, address: str) -> str:
        return checked_git_address(address, self.local_allowed)

    def options(self) -> tuple[str, ...]:
        return SAFE_TRANSPORTS + (LOCAL_TRANSPORT if self.local_allowed else ())
