import html
import subprocess


class KDialog:
    def ask(self, title: str, question: str, suggested: str) -> str | None:
        answered = _kdialog("--title", title, "--inputbox", html.escape(question, quote=False), *_not_an_option(suggested))
        return answered.stdout.strip() if answered and answered.returncode == 0 else None

    def choose(self, title: str, question: str, options: list[str]) -> str | None:
        listed = [part for number, option in enumerate(options) for part in (str(number), html.escape(option, quote=False))]
        answered = _kdialog("--title", title, "--menu", html.escape(question, quote=False), *listed)
        picked = answered.stdout.strip() if answered and answered.returncode == 0 else ""
        return options[int(picked)] if picked.isdigit() and int(picked) < len(options) else None

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
