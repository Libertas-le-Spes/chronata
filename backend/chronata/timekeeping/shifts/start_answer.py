from dataclasses import dataclass

LATE = "late"
AFTER_SHIFT = "after_shift"
OVERTIME = "overtime"
NORMAL_HOURS = "normal hours"


@dataclass(frozen=True)
class StartAnswer:
    late: bool = False
    other_project: bool = False
    overtime: bool = False
    normal_hours: bool = False

    def data(self) -> dict:
        data = {}
        if self.late:
            data[LATE] = True
        if self.other_project:
            data[LATE] = False
        if self.overtime:
            data[AFTER_SHIFT] = OVERTIME
        if self.normal_hours:
            data[AFTER_SHIFT] = NORMAL_HOURS
        return data


def start_answer_in(data: dict) -> StartAnswer:
    late = data.get(LATE)
    after_shift = data.get(AFTER_SHIFT)
    return StartAnswer(late is True, late is False, after_shift == OVERTIME, after_shift == NORMAL_HOURS)
