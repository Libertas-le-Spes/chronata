from typing import Callable

from chronata.entrypoints.web.page_state import page_state
from chronata.presenters.readable_copy import label_folder
from chronata.use_cases.outcome import Outcome
from chronata.use_cases.verification import verify


def reads(app) -> dict[str, Callable[[dict], dict]]:
    return {
        "/api/state": lambda query: page_state(app),
        "/api/label-check": lambda query: _label_check(app, query.get("text", "")),
        "/api/verify": lambda query: {"problems": verify(app.log.record, app.timestamper, app.history).problems},
    }


def dialogs(app) -> dict[str, Callable[[dict], dict]]:
    return {
        "/api/choose-folder": lambda body: {"path": app.desktop.choose_folder()},
    }


def changes(app) -> dict[str, Callable[[dict], Outcome]]:
    return {
        "/api/in": lambda body: app.clocking.clock_in(body.get("at"), body.get("note"), body.get("label"), bool(body.get("newLabel")), bool(body.get("offDefault"))),
        "/api/out": lambda body: app.clocking.clock_out(body.get("at"), body.get("note")),
        "/api/add": lambda body: app.corrections.add(body.get("date"), body.get("start"), body.get("end"), body.get("reason"), body.get("note"),
                                                     body.get("label", ""), bool(body.get("newLabel"))),
        "/api/label": lambda body: app.labels.label_shift(int(body["id"]), body.get("label", ""), bool(body.get("newLabel"))),
        "/api/default-label": lambda body: app.labels.set_default(body.get("label", ""), bool(body.get("newLabel"))),
        "/api/labels/rename": lambda body: app.labels.rename(body.get("from", ""), body.get("to", ""), bool(body.get("newLabel"))),
        "/api/correct": lambda body: app.corrections.correct(int(body["id"]), body.get("start"), body.get("end"), body.get("reason")),
        "/api/strike": lambda body: app.corrections.strike(int(body["id"]), body.get("reason")),
        "/api/explain": lambda body: app.corrections.explain_break(int(body["id"]), body.get("start", ""), body.get("reason")),
        "/api/paid": lambda body: app.payments.record(
            body.get("from"), body.get("to"), float(body.get("hours", "")), bool(body.get("timeOff")), body.get("reference")
        ),
        "/api/save": lambda body: app.log.save_now(),
        "/api/places/add": lambda body: app.saving.add_place(app.log, body.get("kind", ""), body.get("name", ""), body.get("target", ""),
                                                             body.get("username", ""), body.get("password", ""), body.get("folder", "")),
        "/api/places/remove": lambda body: app.saving.remove_place(body.get("id", "")),
        "/api/setup": lambda body: app.setup.configure(body.get("lunch", ""), body.get("shift", ""), body.get("label"), bool(body.get("newLabel"))),
    }


def _label_check(app, typed: str) -> dict:
    choice = app.labels.check(typed)
    return {"label": choice.label, "exists": choice.exists, "folder": label_folder(choice.label) if choice.label else "",
            "nearMisses": list(choice.near_misses)}
