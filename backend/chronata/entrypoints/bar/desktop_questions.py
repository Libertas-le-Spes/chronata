from chronata.use_cases.questions.questions import Question


def ask(desktop, question: Question) -> tuple[str | None, dict] | None:
    picked = desktop.choose(question.text, [choice.caption for choice in question.choices])
    choice = next((choice for choice in question.choices if choice.caption == picked), None)
    if choice is None:
        return None
    typed = {}
    for needed in choice.inputs:
        value = desktop.ask(f"{needed.prompt}\nFor example {needed.example}.", "")
        if value is None:
            return None
        typed[needed.name] = value
    return choice.label, {**choice.answers, **typed}
