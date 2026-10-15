from dataclasses import replace

from chronata.entrypoints.bar.desktop_questions import ask
from chronata.entrypoints.web.server import DEFAULT_PORT, page_url
from chronata.timekeeping.labels.labels import known_labels
from chronata.timekeeping.shifts.durations import hours
from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.questions.questions import Answers, Choice, Question

STARTED_WHEN_THE_PC_CAME_ON = "started when the PC came on"


def ask_and_clock_in(app) -> None:
    if not app.desktop.can_ask():
        app.desktop.open_page(page_url(DEFAULT_PORT) + "#clock-in")
        return
    typed = app.desktop.ask(_which_label(app), app.labels.suggested())
    if typed is None:
        return
    start = _when_started(app)
    if start is not None:
        _clock_in_on(app, typed, start.get("at"), start.get("note"))


def _which_label(app) -> str:
    pc_on = app.pc.on_since()
    known = known_labels(app.log.shifts())
    lines = ["Clock in on which client or project?",
             f"Your labels: {', '.join(known)}" if known else "",
             f"The PC has been on since {pc_on:%H:%M} ({hours(app.log.clock() - pc_on)})." if pc_on else ""]
    return "\n".join(line for line in lines if line)


def _when_started(app) -> dict | None:
    since = app.clocking.unclocked_since()
    if since is None:
        return {}
    question = Question(f"Have you been working since the PC came on at {since:%H:%M} ({hours(app.log.clock() - since)} ago), or are you starting now?",
                        [Choice(f"Since {since:%H:%M}", answers={"at": since.isoformat(), "note": STARTED_WHEN_THE_PC_CAME_ON}), Choice("From now")])
    answer = ask(app.desktop, question)
    return None if answer is None else answer[1]


def _clock_in_on(app, label: str, at: str | None = None, note: str | None = None, answers: Answers = Answers()) -> None:
    try:
        outcome = app.clocking.clock_in(at, note, label, answers)
    except Question as question:
        answer = ask(app.desktop, question)
        if answer is not None:
            relabelled, given = answer
            _clock_in_on(app, label if relabelled is None else relabelled, at, note, replace(answers, **given))
        return
    except UserError as error:
        app.desktop.notify("Could not clock in", str(error))
        return
    app.desktop.notify(outcome.headline, outcome.warning or "")
