from datetime import datetime


def iso(moment: datetime | None) -> str | None:
    return moment.isoformat() if moment else None
