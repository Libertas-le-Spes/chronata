from dataclasses import asdict

from chronata.timekeeping.record.record import TamperedRecord
from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.log.ports import CannotCheck
from chronata.use_cases.questions.questions import Question

ASKS_FOR_AN_ANSWER = 409
REFUSED = 400
CANNOT_CHECK = 503

REPLIES = [
    (Question, ASKS_FOR_AN_ANSWER, lambda error: {"error": str(error), "question": {"text": error.text, "choices": [asdict(c) for c in error.choices]}}),
    (CannotCheck, CANNOT_CHECK, lambda error: {"error": str(error)}),
    ((UserError, TamperedRecord), REFUSED, lambda error: {"error": str(error)}),
    ((KeyError, ValueError), REFUSED, lambda error: {"error": "some fields are missing or not numbers"}),
]


def refusal(error: Exception) -> tuple[int, dict] | None:
    return next(((status, reply(error)) for kinds, status, reply in REPLIES if isinstance(error, kinds)), None)
