from typing import ClassVar, Protocol


class NewEntry(Protocol):
    kind: ClassVar[str]

    def data(self) -> dict: ...


def with_note(data: dict, note: str | None) -> dict:
    return {**data, "note": note.strip()} if note and note.strip() else data


def with_label(label: str | None) -> dict:
    return {"label": label.strip()} if label and label.strip() else {}
