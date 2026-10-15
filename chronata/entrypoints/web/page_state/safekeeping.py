from chronata.entrypoints.web.page_state.snapshot import Snapshot


def state(app, taken: Snapshot) -> dict:
    kinds = app.saving.places.kinds()
    newest, by = app.saving.stamped()
    return {
        "integrity": {"entries": app.log.entry_count(), "problems": app.log.problems()},
        "saving": {
            "kinds": {
                kind: {"label": d.label, "asksFor": d.asks_for, "example": d.example, "onThisComputer": d.on_this_computer,
                       "needsFolder": d.needs_folder, "needsLogin": d.needs_login, "explanation": d.explanation}
                for kind, d in kinds.items()
            },
            "places": [
                {"id": place.id, "kind": place.kind, "kindLabel": kinds[place.kind].label, "name": place.name, "target": place.target,
                 "saved": last.get("saved"), "error": last.get("error")}
                for place, last in app.saving.statuses()
            ],
            "stamped": {"upTo": newest, "by": [{"authority": s.authority_name, "time": s.time.isoformat()} for s in by]},
        },
    }
