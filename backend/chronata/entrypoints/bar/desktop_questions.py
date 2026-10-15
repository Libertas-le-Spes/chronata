from chronata.use_cases.questions.questions import Choice, Question


def ask(desktop, question: Question) -> tuple[str | None, dict] | None:
    picked = desktop.choose(question.text, [choice.caption for choice in question.choices])
    choice = next((choice for choice in question.choices if choice.caption == picked), None)
    if choice is None:
        return None
    typed = _typed(desktop, choice)
    return None if typed is None else (choice.label, {**choice.answers, **typed})


def _typed(desktop, choice: Choice) -> dict | None:
    typed = {}
    for needed in choice.inputs:
        value = desktop.ask(f"{needed.prompt}\nFor example {needed.example}.", needed.value)
        if value is None:
            return None
        if needed.opts_out and not value.strip():
            break
        typed[needed.name] = value
    return typed
