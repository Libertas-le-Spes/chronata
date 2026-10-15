import subprocess


class KDialog:
    def ask(self, title: str, question: str, suggested: str) -> str | None:
        answered = _kdialog("--title", title, "--inputbox", question, suggested)
        return answered.stdout.strip() if answered and answered.returncode == 0 else None

    def choose(self, title: str, question: str, options: list[str]) -> str | None:
        listed = [part for option in options for part in (option, option)]
        answered = _kdialog("--title", title, "--menu", question, *listed)
        return answered.stdout.strip() or None if answered and answered.returncode == 0 else None

    def pick_folder(self, title: str) -> str | None:
        chosen = _kdialog("--title", title, "--getexistingdirectory")
        return chosen.stdout.strip() or None if chosen and chosen.returncode == 0 else None


def _kdialog(*arguments: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["kdialog", *arguments], capture_output=True, text=True, check=False, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return None
