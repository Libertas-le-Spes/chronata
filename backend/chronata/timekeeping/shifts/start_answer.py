from dataclasses import dataclass

LATE = "late"
OVERTIME_AFTER_SHIFT = "overtime_after_shift"


@dataclass(frozen=True)
class StartAnswer:
    late: bool | None = None
    overtime_after_shift: bool | None = None

    @property
    def said_late(self) -> bool:
        return self.late is True

    @property
    def said_overtime(self) -> bool:
        return self.overtime_after_shift is True

    def data(self) -> dict:
        data = {}
        if self.late is not None:
            data[LATE] = self.late
        if self.overtime_after_shift is not None:
            data[OVERTIME_AFTER_SHIFT] = self.overtime_after_shift
        return data


def start_answer_in(data: dict) -> StartAnswer:
    return StartAnswer(_yes_or_no(data.get(LATE)), _yes_or_no(data.get(OVERTIME_AFTER_SHIFT)))


def _yes_or_no(stored) -> bool | None:
    if isinstance(stored, bool):
        return stored
    return None
