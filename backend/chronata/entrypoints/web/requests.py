from functools import partial
from typing import Callable

from chronata.entrypoints.web.page_facts import page_facts
from chronata.presenters.page.page_state import page_state
from chronata.presenters.readable_copy.readable_copy import label_folder
from chronata.use_cases.log.outcome import Outcome, UserError
from chronata.use_cases.log.verification import verify
from chronata.use_cases.questions.questions import Answers


def reads(app) -> dict[str, Callable[[dict], dict]]:
    return {
        "/api/state": lambda query: page_state(page_facts(app)),
        "/api/label-check": lambda query: _label_check(app, query.get("text", "")),
        "/api/verify": lambda query: {"problems": verify(app.log.record, app.timestamper, app.history).problems},
    }


def dialogs(app) -> dict[str, Callable[[dict], dict]]:
    return {
        "/api/choose-folder": lambda body: {"path": app.desktop.choose_folder()},
    }


def changes(app) -> dict[str, Callable[[dict], Outcome]]:
    return {
        "/api/in": lambda body: app.clocking.clock_in(body.get("at"), body.get("note"), body.get("label"), _answers(body)),
        "/api/out": lambda body: app.clocking.clock_out(body.get("at"), body.get("note")),
        "/api/add": lambda body: app.corrections.add(body.get("date"), body.get("start"), body.get("end"), body.get("reason"), body.get("note"),
                                                     body.get("label", ""), _answers(body)),
        "/api/label": lambda body: app.labels.label_shifts(_ids(body), body.get("label", ""), _answers(body)),
        "/api/default-label": lambda body: app.labels.set_default(body.get("label", ""), _answers(body)),
        "/api/labels/hours": lambda body: app.setup.set_hours(body.get("label", ""), _answers(body)),
        "/api/labels/rename": lambda body: app.labels.rename(body.get("from", ""), body.get("to", ""), _answers(body)),
        "/api/correct": lambda body: app.corrections.correct(_ids(body), body.get("start"), body.get("end"), body.get("reason"),
                                                                 _answers(body)),
        "/api/mistake": lambda body: app.corrections.mark_mistake(_ids(body), body.get("reason")),
        "/api/waive": partial(_waive, app),
        "/api/withdraw-waiver": partial(_withdraw_waiver, app),
        "/api/explain": partial(_explain, app),
        "/api/compensation": lambda body: app.compensations.record(
            body.get("label", ""), body.get("from"), body.get("to"), float(body.get("hours", "")), body.get("kind", ""),
            body.get("reference"), _answers(body)
        ),
        "/api/reminders": partial(_reminders, app),
        "/api/save": lambda body: app.log.save_now(),
        "/api/places/add": lambda body: app.saving.add_place(app.log, body.get("kind", ""), body.get("name", ""), body.get("target", ""),
                                                             body.get("username", ""), body.get("password", ""), body.get("folder", "")),
        "/api/places/remove": lambda body: app.saving.remove_place(body.get("id", "")),
        "/api/setup": lambda body: app.setup.configure(_answers(body), body.get("label")),
    }


def _reminders(app, body: dict) -> Outcome:
    if body.get("off") is True:
        return app.reminder_setting.turn_off()
    return app.reminder_setting.remind_every(body.get("every"))


def _explain(app, body: dict) -> Outcome:
    return app.corrections.explain_break(_shift_id(body.get("id")), _text(body, "start"), _text(body, "reason"))


def _waive(app, body: dict) -> Outcome:
    return app.waivers.waive(_shift_ids(body), _text(body, "start"), _text(body, "end"), _text(body, "reason"))


def _withdraw_waiver(app, body: dict) -> Outcome:
    return app.waivers.withdraw(_shift_id(body.get("id")), _text(body, "start"), _text(body, "reason"))


def _shift_ids(body: dict) -> list[int]:
    given = body.get("ids")
    if not isinstance(given, list):
        raise UserError("choose a shift")
    chosen = []
    for shift_id in given:
        chosen.append(_shift_id(shift_id))
    return chosen


def _shift_id(given) -> int:
    if isinstance(given, bool) or not isinstance(given, int):
        raise UserError("choose a shift")
    return given


def _text(body: dict, name: str) -> str:
    given = body.get(name, "")
    if not isinstance(given, str):
        raise UserError(f"the {name} has to be text")
    return given


def _ids(body: dict) -> list[int]:
    return [int(shift_id) for shift_id in body.get("ids", [])]


def _answers(body: dict) -> Answers:
    given = body.get("answers", {})
    if not isinstance(given, dict):
        raise UserError("the answers have to be sent as named answers")
    return Answers.from_dict(given)


def _label_check(app, typed: str) -> dict:
    choice = app.labels.check(typed)
    return {"label": choice.label, "exists": choice.exists, "folder": label_folder(choice.label) if choice.label else "",
            "nearMisses": list(choice.near_misses)}
