from dataclasses import dataclass, replace

LATE = "late"
OVERTIME_AFTER_SHIFT = "overtime_after_shift"
ANSWERED_FOR = "answered_for"


@dataclass(frozen=True)
class StartAnswer:
    late: bool | None = None
    overtime_after_shift: bool | None = None
    label: str = ""

    def said_late_for(self, label: str) -> bool:
        if self.label != label:
            return False
        return self.late is True

    def said_overtime_for(self, label: str) -> bool:
        if self.label != label:
            return False
        return self.overtime_after_shift is True

    def renamed(self, old: str, new: str) -> "StartAnswer":
        if self.label != old:
            return self
        return replace(self, label=new)

    def data(self) -> dict:
        data = {}
        if self.late is not None:
            data[LATE] = self.late
        if self.overtime_after_shift is not None:
            data[OVERTIME_AFTER_SHIFT] = self.overtime_after_shift
        if data:
            data[ANSWERED_FOR] = self.label
        return data


def start_answer_in(data: dict) -> StartAnswer:
    return StartAnswer(_yes_or_no(data.get(LATE)), _yes_or_no(data.get(OVERTIME_AFTER_SHIFT)), _text(data.get(ANSWERED_FOR)))


def _yes_or_no(stored) -> bool | None:
    if isinstance(stored, bool):
        return stored
    return None


def _text(stored) -> str:
    if isinstance(stored, str):
        return stored
    return ""
