from chronata.presenters.page.facts import PageFacts


def state(facts: PageFacts) -> dict:
    kinds = facts.place_kinds
    newest, by = facts.newest_stamped, facts.stamped_by
    return {
        "integrity": {"entries": facts.entry_count, "problems": facts.problems},
        "saving": {
            "kinds": {
                kind: {"label": d.label, "asksFor": d.asks_for, "example": d.example, "onThisComputer": d.on_this_computer,
                       "needsFolder": d.needs_folder, "needsLogin": d.needs_login, "explanation": d.explanation}
                for kind, d in kinds.items()
            },
            "places": [
                {"id": place.id, "kind": place.kind, "kindLabel": kinds[place.kind].label, "name": place.name, "target": place.target,
                 "saved": last.get("saved"), "error": last.get("error")}
                for place, last in facts.places
            ],
            "stamped": {"upTo": newest, "by": [{"authority": s.authority_name, "time": s.time.isoformat()} for s in by]},
        },
    }
