from functools import partial
from typing import Callable

from chronata.timekeeping.shifts.durations import hours
from chronata.use_cases.away.away_stretch import AwayStretch
from chronata.use_cases.log.outcome import Outcome, UserError

STILL_WORKING = "Still working"
CLOCK_OUT_NOW = "Clock out now"
WHAT_KEPT_YOU = "What kept you away from the PC? For example, a meeting."
WHY_NOT_WORK = "Why was that time not work? For example, forgot to clock out."


def ask_after_away(app, stretch: AwayStretch) -> None:
    left, back = f"{stretch.since:%H:%M}", f"{stretch.back:%H:%M}"
    choices = {
        STILL_WORKING: _still_working,
        CLOCK_OUT_NOW: _clock_out_now,
        f"Clock out at {left}, when I left": _clock_out_when_left,
        f"Waive {left}–{back} and keep working": _waive,
    }
    question = f"You were away from the PC from {left} to {back} ({hours(stretch.back - stretch.since)}), after your shift. Were you working?"
    picked = app.desktop.choose(question, list(choices))
    if picked not in choices:
        return
    choices[picked](app, stretch)


def _still_working(app, stretch: AwayStretch) -> None:
    app.away.settled()


def _clock_out_now(app, stretch: AwayStretch) -> None:
    reason = _reason(app, WHAT_KEPT_YOU)
    if reason is None:
        return
    _settle_with(app, "Could not clock out", partial(app.clocking.clock_out, None, reason))


def _clock_out_when_left(app, stretch: AwayStretch) -> None:
    note = f"away from the PC from {stretch.since:%H:%M}"
    _settle_with(app, "Could not clock out", partial(app.clocking.clock_out, stretch.since.isoformat(), note))


def _waive(app, stretch: AwayStretch) -> None:
    reason = _reason(app, WHY_NOT_WORK)
    if reason is None:
        return
    waiving = partial(app.waivers.waive, [stretch.shift], stretch.since.isoformat(), stretch.back.isoformat(), reason)
    _settle_with(app, "Could not waive that time", waiving)


def _reason(app, prompt: str) -> str | None:
    typed = app.desktop.ask(prompt, "")
    if typed is None:
        return None
    if not typed.strip():
        app.desktop.notify("Nothing was changed", "A reason is needed, so the record explains itself.")
        return None
    return typed.strip()


def _settle_with(app, failure: str, change: Callable[[], Outcome]) -> None:
    try:
        outcome = change()
    except UserError as error:
        app.desktop.notify(failure, str(error))
        return
    app.away.settled()
    app.desktop.notify(outcome.headline, _warning_of(outcome))


def _warning_of(outcome: Outcome) -> str:
    if outcome.warning is None:
        return ""
    return outcome.warning
