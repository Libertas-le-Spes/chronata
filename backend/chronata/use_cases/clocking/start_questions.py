from datetime import datetime

from chronata.timekeeping.hours.label_hours import LabelHours
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.shifts.shifts import Shift, completed
from chronata.timekeeping.shifts.start_answer import StartAnswer
from chronata.use_cases.questions.questions import AfterShift, Answers, LateOrOtherProject


def start_answer(hours: LabelHours, label: str, start: datetime, all_shifts: list[Shift], answers: Answers) -> StartAnswer:
    working_day = hours.for_label(label)
    if working_day is None or start.weekday() not in working_day.workdays:
        return StartAnswer()
    earlier = _earlier_today(all_shifts, start)
    if not earlier:
        return _first_of_the_day(working_day, label, start, answers)
    if _on_label(earlier, label) or not _during_shift(working_day, start):
        return StartAnswer()
    return _late_or_other_project(label, answers)


def _first_of_the_day(working_day: WorkingDay, label: str, start: datetime, answers: Answers) -> StartAnswer:
    if start.time() < working_day.shift_end:
        return StartAnswer()
    if answers.overtime:
        return StartAnswer(overtime=True)
    if answers.normal_hours:
        return StartAnswer(normal_hours=True)
    raise AfterShift(label, f"{working_day.shift_end:%H:%M}")


def _late_or_other_project(label: str, answers: Answers) -> StartAnswer:
    if answers.late:
        return StartAnswer(late=True)
    if answers.other_project:
        return StartAnswer(other_project=True)
    raise LateOrOtherProject(label)


def _earlier_today(all_shifts: list[Shift], start: datetime) -> list[Shift]:
    found = []
    for shift in completed(all_shifts):
        if shift.start.date() == start.date() and shift.start < start:
            found.append(shift)
    return found


def _on_label(shifts: list[Shift], label: str) -> bool:
    for shift in shifts:
        if shift.label == label:
            return True
    return False


def _during_shift(working_day: WorkingDay, start: datetime) -> bool:
    return working_day.shift_start < start.time() < working_day.shift_end
