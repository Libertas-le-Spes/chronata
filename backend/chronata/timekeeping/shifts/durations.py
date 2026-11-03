from datetime import timedelta

NONE = timedelta()


def hours(span: timedelta) -> str:
    total = minutes(span)
    if total < 0:
        return f"-{_clock(-total)}"
    return _clock(total)


def minutes(span: timedelta) -> int:
    return round(span.total_seconds() / 60)


def _clock(total: int) -> str:
    return f"{total // 60}:{total % 60:02d}"
