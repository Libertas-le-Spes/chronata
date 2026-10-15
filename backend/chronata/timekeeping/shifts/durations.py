from datetime import timedelta


def hours(span: timedelta) -> str:
    total = round(span.total_seconds() / 60)
    return f"{total // 60}:{total % 60:02d}"


def minutes(span: timedelta) -> int:
    return round(span.total_seconds() / 60)
