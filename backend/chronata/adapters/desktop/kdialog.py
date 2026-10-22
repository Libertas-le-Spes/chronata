import html
import subprocess


class KDialog:
    def ask(self, title: str, question: str, suggested: str) -> str | None:
        answered = _kdialog("--title", title, "--inputbox", html.escape(question, quote=False), *_not_an_option(suggested))
        return answered.stdout.strip() if answered and answered.returncode == 0 else None

    def choose(self, title: str, question: str, options: list[str]) -> str | None:
        listed = [part for option in options if not option.startswith("-") for part in (option, html.escape(option, quote=False))]
        answered = _kdialog("--title", title, "--menu", html.escape(question, quote=False), *listed)
        return answered.stdout.strip() or None if answered and answered.returncode == 0 else None

    def pick_folder(self, title: str) -> str | None:
        chosen = _kdialog("--title", title, "--getexistingdirectory")
        return chosen.stdout.strip() or None if chosen and chosen.returncode == 0 else None


def _not_an_option(suggested: str) -> list[str]:
    return [] if suggested.startswith("-") else [suggested]


def _kdialog(*arguments: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["kdialog", *arguments], capture_output=True, text=True, check=False, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return None
