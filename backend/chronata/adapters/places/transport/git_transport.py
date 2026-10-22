from chronata.adapters.places.addresses import checked_git_address

SAFE_TRANSPORTS = ("-c", "protocol.allow=never", "-c", "protocol.https.allow=always", "-c", "protocol.ssh.allow=always",
                   "-c", "protocol.file.allow=always", "-c", "core.hooksPath=/dev/null")


class GitTransport:
    def checked(self, address: str) -> str:
        return checked_git_address(address)

    def options(self) -> tuple[str, ...]:
        return SAFE_TRANSPORTS
