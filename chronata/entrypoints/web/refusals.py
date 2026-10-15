from chronata.timekeeping.record import TamperedRecord
from chronata.use_cases.outcome import OffDefaultLabel, UnconfirmedLabel, UserError

ASKS_FOR_CONFIRMATION = 409
REFUSED = 400


def refusal(error: Exception) -> tuple[int, dict] | None:
    if isinstance(error, UnconfirmedLabel):
        return ASKS_FOR_CONFIRMATION, {"error": str(error), "label": error.label, "nearMisses": list(error.near_misses)}
    if isinstance(error, OffDefaultLabel):
        return ASKS_FOR_CONFIRMATION, {"error": str(error), "label": error.label, "defaultLabel": error.default_label, "offDefault": True}
    if isinstance(error, (UserError, TamperedRecord)):
        return REFUSED, {"error": str(error)}
    if isinstance(error, (KeyError, ValueError)):
        return REFUSED, {"error": "some fields are missing or not numbers"}
    return None
