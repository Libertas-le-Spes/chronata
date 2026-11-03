from datetime import datetime
from functools import partial
from typing import Callable

from chronata.timekeeping.shifts.durations import hours
from chronata.use_cases.away.away import TimeAway
from chronata.use_cases.log.outcome import Outcome, UserError

WHAT_KEPT_YOU = "What kept you away from the PC? For example, a meeting."
WHY_NOT_WORK = "Why was that time not work? For example, forgot to clock out."


class StillWorking:
    def caption(self, away: TimeAway) -> str:
        return "Still working"

    def act(self, app, away: TimeAway) -> None:
        app.away.settled()


class ClockOutNow:
    def caption(self, away: TimeAway) -> str:
        return "Clock out now"

    def act(self, app, away: TimeAway) -> None:
        reason = _reason(app, WHAT_KEPT_YOU)
        if reason is None:
            return
        _settle_with(app, "Could not clock out", partial(app.clocking.clock_out, None, reason))


class ClockOutWhenLeft:
    def caption(self, away: TimeAway) -> str:
        return f"Clock out at {_clock(away.stretch.since)}, when I left"

    def act(self, app, away: TimeAway) -> None:
        left = away.stretch.since
        _settle_with(app, "Could not clock out", partial(app.clocking.clock_out, left.isoformat(), f"away from the PC from {_clock(left)}"))


class WaiveAndKeepWorking:
    def caption(self, away: TimeAway) -> str:
        return f"Waive {_clock(away.stretch.since)}–{_clock(away.stretch.back)} and keep working"

    def act(self, app, away: TimeAway) -> None:
        reason = _reason(app, WHY_NOT_WORK)
        if reason is None:
            return
        stretch = away.stretch
        waiving = partial(app.waivers.waive, [stretch.shift], stretch.since.isoformat(), stretch.back.isoformat(), reason)
        _settle_with(app, "Could not waive that time", waiving)


def ask_after_away(app, away: TimeAway) -> None:
    answers = _answers_for(away)
    picked = app.desktop.choose(_question(away), [answer.caption(away) for answer in answers])
    for answer in answers:
        if answer.caption(away) == picked:
            answer.act(app, away)
            return


def _answers_for(away: TimeAway) -> list:
    answers = [StillWorking(), ClockOutNow()]
    if away.left_after_clocking_in:
        answers.append(ClockOutWhenLeft())
    answers.append(WaiveAndKeepWorking())
    return answers


def _question(away: TimeAway) -> str:
    stretch = away.stretch
    span = f"{_clock(stretch.since)} to {_clock(stretch.back)} ({hours(stretch.back - stretch.since)})"
    return f"You were away from the PC from {span}, {away.occasion}. Were you working?"


def _clock(moment: datetime) -> str:
    return f"{moment:%H:%M}"


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
