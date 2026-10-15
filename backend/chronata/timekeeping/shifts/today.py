from datetime import datetime, timedelta

from chronata.timekeeping.shifts.shifts import Break, Shift, completed, open_shift

UNCLOCKED_WORTH_ASKING = timedelta(minutes=5)


def resumable(all_shifts: list[Shift], now: datetime) -> Shift | None:
    finished = [shift for shift in completed(all_shifts) if shift.end <= now]
    latest = max(finished, key=lambda shift: shift.end, default=None)
    return latest if latest and latest.start.date() == now.date() else None


def day_so_far(all_shifts: list[Shift], now: datetime) -> tuple[datetime, timedelta] | None:
    current = open_shift(all_shifts)
    if current is None:
        return None
    today = [shift for shift in all_shifts if _counts_with(shift, current, now)] + [current]
    return min(shift.start for shift in today), sum((shift.worked(shift.end or now) for shift in today), timedelta())


def unclocked_since(all_shifts: list[Shift], pc_on: datetime | None, now: datetime) -> datetime | None:
    if not _pc_on_a_while_today(pc_on, now) or open_shift(all_shifts):
        return None
    clocked_since_pc_on = any(shift.end > pc_on for shift in completed(all_shifts))
    return None if clocked_since_pc_on else pc_on


def _counts_with(shift: Shift, current: Shift, now: datetime) -> bool:
    if shift is current or shift.voided:
        return False
    return shift.start.date() == now.date() and shift.label == current.label


def _pc_on_a_while_today(pc_on: datetime | None, now: datetime) -> bool:
    if pc_on is None or pc_on.date() != now.date():
        return False
    return now - pc_on >= UNCLOCKED_WORTH_ASKING


def unexplained_pc_breaks(all_shifts: list[Shift], day) -> list[tuple[Shift, Break]]:
    return [(shift, gap) for shift in all_shifts for gap in shift.breaks
            if gap.unexplained_pc_off and gap.start.date() == day]
