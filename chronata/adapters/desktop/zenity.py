import subprocess

CANCEL = "Cancel"


class Zenity:
    def ask(self, title: str, question: str, suggested: str) -> str | None:
        answered = _zenity("--entry", f"--title={title}", f"--text={question}", f"--entry-text={suggested}")
        return answered.stdout.strip() if answered and answered.returncode == 0 else None

    def choose(self, title: str, question: str, options: list[str]) -> str | None:
        buttons = [f"--extra-button={option}" for option in [*options, CANCEL]]
        answered = _zenity("--question", "--switch", "--no-markup", f"--title={title}", f"--text={question}", *buttons)
        picked = answered.stdout.strip() if answered else ""
        return picked if picked and picked != CANCEL else None

    def pick_folder(self, title: str) -> str | None:
        chosen = _zenity("--file-selection", "--directory", f"--title={title}")
        return chosen.stdout.strip() or None if chosen and chosen.returncode == 0 else None


def _zenity(*arguments: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["zenity", *arguments], capture_output=True, text=True, check=False, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return None
