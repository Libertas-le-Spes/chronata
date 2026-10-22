import shutil
import subprocess

from chronata.use_cases.log.ports import SaveError

SERVICE = "chronata"
ANSWER_SECONDS = 60


class SecretService:
    def keep(self, key: str, secret: str) -> None:
        kept = self._run(["store", f"--label=Chronata: {key}", "service", SERVICE, "place", key], secret)
        if kept.returncode != 0:
            raise SaveError(f"the desktop keyring did not keep the password: {kept.stderr.strip() or 'it may be locked'}")

    def find(self, key: str) -> str | None:
        found = self._run(["lookup", "service", SERVICE, "place", key])
        return found.stdout if found.returncode == 0 and found.stdout else None

    def forget(self, key: str) -> None:
        self._run(["clear", "service", SERVICE, "place", key])

    def _run(self, args: list[str], secret: str = "") -> subprocess.CompletedProcess:
        if shutil.which("secret-tool") is None:
            raise SaveError("Chronata keeps passwords only in the desktop keyring, and secret-tool (from libsecret) is not installed")
        try:
            return subprocess.run(["secret-tool", *args], input=secret, capture_output=True, text=True, check=False, timeout=ANSWER_SECONDS)
        except subprocess.TimeoutExpired:
            raise SaveError("the desktop keyring did not answer; unlock it and try again")
