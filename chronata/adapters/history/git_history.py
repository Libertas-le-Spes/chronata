import subprocess
from pathlib import Path


class GitHistory:
    def __init__(self, directory: Path, watched_file: str):
        self.directory = directory
        self.watched_file = watched_file
        if not (directory / ".git").exists():
            self._git("init", "-q", "-b", "main")

    def commit(self, message: str) -> None:
        self._git("add", "-A")
        self._git("commit", "-q", "-m", message)

    def rewrites(self) -> list[str]:
        revisions = self._git("rev-list", "--reverse", "HEAD", "--", self.watched_file, check=False).stdout.split()
        problems = []
        before = ""
        for revision in revisions:
            after = self._git("show", f"{revision}:{self.watched_file}", check=False).stdout
            if not after.startswith(before):
                problems.append(f"commit {revision[:10]} changed lines that an earlier commit had already saved")
            before = after
        return problems

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(self.directory), *args], capture_output=True, text=True, check=check)
