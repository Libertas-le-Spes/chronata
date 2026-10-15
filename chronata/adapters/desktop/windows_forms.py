import base64
import os
import subprocess
from pathlib import Path

FORMS = Path(__file__).parent / "forms"


class WindowsForms:
    def ask(self, title: str, question: str, suggested: str) -> str | None:
        answered = _show(["window.ps1", "ask.ps1"], CHRONATA_TITLE=title, CHRONATA_QUESTION=question, CHRONATA_SUGGESTED=suggested)
        return answered.stdout.strip() if answered and answered.returncode == 0 else None

    def choose(self, title: str, question: str, options: list[str]) -> str | None:
        answered = _show(["window.ps1", "choose.ps1"], CHRONATA_TITLE=title, CHRONATA_QUESTION=question, CHRONATA_OPTIONS="\n".join(options))
        return answered.stdout.strip() or None if answered and answered.returncode == 0 else None

    def pick_folder(self, title: str) -> str | None:
        chosen = _show(["pick_folder.ps1"], CHRONATA_TITLE=title)
        return chosen.stdout.strip() or None if chosen and chosen.returncode == 0 else None


def script_for(parts: list[str]) -> str:
    return "\n".join((FORMS / part).read_text(encoding="utf-8") for part in parts)


def _show(parts: list[str], **values: str) -> subprocess.CompletedProcess | None:
    encoded = base64.b64encode(script_for(parts).encode("utf-16-le")).decode("ascii")
    command = ["powershell", "-NoProfile", "-NonInteractive", "-Sta", "-EncodedCommand", encoded]
    try:
        return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False, timeout=600,
                              env={**os.environ, **values}, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        return None
