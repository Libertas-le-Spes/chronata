import subprocess
from pathlib import Path


class AuditTrail:
    def __init__(self, directory: Path):
        self.directory = directory

    def ensure(self) -> None:
        if not (self.directory / ".git").exists():
            self._git("init", "-q", "-b", "main")

    def commit(self, message: str) -> None:
        self._git("add", "-A")
        self._git("commit", "-q", "-m", message)

    def remote(self) -> str | None:
        found = self._git("remote", "get-url", "origin", check=False)
        return found.stdout.strip() if found.returncode == 0 else None

    def add_remote(self, name: str, url: str) -> None:
        self._git("remote", "add", name, url)

    def remove_remote(self, name: str) -> None:
        self._git("remote", "remove", name, check=False)

    def push(self, remote: str, timeout: float = 30) -> str | None:
        try:
            pushed = self._git("push", "-q", remote, "HEAD:main", check=False, timeout=timeout)
        except subprocess.TimeoutExpired:
            return f"did not answer in {timeout:g}s; will try again on the next save"
        if pushed.returncode != 0:
            return f"{pushed.stderr.strip() or 'push failed'}; will try again on the next save"
        return None

    def rewrites(self, filename: str) -> list[str]:
        revisions = self._git("rev-list", "--reverse", "HEAD", "--", filename, check=False).stdout.split()
        problems = []
        before = ""
        for revision in revisions:
            after = self._git("show", f"{revision}:{filename}", check=False).stdout
            if not after.startswith(before):
                problems.append(f"commit {revision[:10]} changed lines that an earlier commit had already saved")
            before = after
        return problems

    def _git(self, *args: str, check: bool = True, timeout: float | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(self.directory), *args],
            capture_output=True, text=True, check=check, timeout=timeout,
        )
