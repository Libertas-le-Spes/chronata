from typing import Callable

from chronata.entrypoints.web.page_facts import page_facts
from chronata.presenters.page.page_state import page_state
from chronata.presenters.readable_copy.readable_copy import label_folder
from chronata.use_cases.log.outcome import Outcome
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
        "/api/labels/hours": lambda body: app.setup.set_hours(body.get("label", ""), body.get("shift", ""), body.get("lunch", ""), bool(body.get("noSetHours"))),
        "/api/labels/rename": lambda body: app.labels.rename(body.get("from", ""), body.get("to", ""), _answers(body)),
        "/api/correct": lambda body: app.corrections.correct(_ids(body), body.get("start"), body.get("end"), body.get("reason")),
        "/api/mistake": lambda body: app.corrections.mark_mistake(_ids(body), body.get("reason")),
        "/api/explain": lambda body: app.corrections.explain_break(int(body["id"]), body.get("start", ""), body.get("reason")),
        "/api/compensation": lambda body: app.compensations.record(
            body.get("label", ""), body.get("from"), body.get("to"), float(body.get("hours", "")), bool(body.get("timeOff")),
            body.get("reference"), _answers(body)
        ),
        "/api/save": lambda body: app.log.save_now(),
        "/api/places/add": lambda body: app.saving.add_place(app.log, body.get("kind", ""), body.get("name", ""), body.get("target", ""),
                                                             body.get("username", ""), body.get("password", ""), body.get("folder", "")),
        "/api/places/remove": lambda body: app.saving.remove_place(body.get("id", "")),
        "/api/setup": lambda body: app.setup.configure(body.get("lunch", ""), body.get("shift", ""), body.get("label"), _answers(body)),
    }


def _ids(body: dict) -> list[int]:
    return [int(shift_id) for shift_id in body.get("ids", [])]


def _answers(body: dict) -> Answers:
    return Answers.from_dict(body.get("answers", {}))


def _label_check(app, typed: str) -> dict:
    choice = app.labels.check(typed)
    return {"label": choice.label, "exists": choice.exists, "folder": label_folder(choice.label) if choice.label else "",
            "nearMisses": list(choice.near_misses)}
