from chronata.timekeeping.shifts.durations import NONE, hours
from chronata.timekeeping.shifts.shifts import Break
from chronata.use_cases.waivers.stretch import Stretch


def waived(pieces: list[Stretch], kept: Stretch | None) -> str:
    spans = " and ".join(_span(piece) for piece in pieces)
    no_longer_counted = sum((piece.length for piece in pieces), NONE)
    return f"waived {pieces[0].begins:%Y-%m-%d} {spans}, {hours(no_longer_counted)} no longer counted{_kept(kept)}"


def nothing_waived(asked: Stretch) -> str:
    return f"nothing waived: {_span(asked)} makes up for coming in late, so it still counts"


def took_back(gap: Break) -> str:
    return f"took back the waiver for {gap.start:%Y-%m-%d %H:%M:%S} to {gap.end:%H:%M:%S}, {hours(gap.end - gap.start)} counted again"


def _kept(kept: Stretch | None) -> str:
    if kept is None:
        return ""
    return f"; kept {_span(kept)} ({hours(kept.length)}), which makes up for coming in late"


def _span(stretch: Stretch) -> str:
    return f"{stretch.begins:%H:%M:%S} to {stretch.ends:%H:%M:%S}"
