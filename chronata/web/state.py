from datetime import datetime, timedelta

from chronata import places, setup, timestamps
from chronata.pc_sessions import PcSession, support
from chronata.rules import Rules, worked_by_label
from chronata.report import LATE_ENOUGH_TO_FLAG
from chronata.settings import DAY_NAMES
from chronata.shifts import Shift, completed, labels, open_shift
from chronata.timesheet import Timesheet


def minutes(span: timedelta) -> int:
    return round(span.total_seconds() / 60)


def state(sheet: Timesheet) -> dict:
    now = sheet.clock()
    rules = sheet.rules
    all_shifts = sheet.shifts()
    all_weeks = sheet.weeks()
    reconciliation = sheet.reconciliation(all_weeks)
    current = open_shift(all_shifts)
    sessions = sheet.pc_sessions()
    this_boot = next((s for s in sessions if s.boot == sheet.boot_id()), None)
    interrupted = sheet.interrupted()
    return {
        "now": now.isoformat(),
        "open": {"id": current.id, "start": current.start.isoformat()} if current else None,
        "interrupted": {
            "start": interrupted.shift.start.isoformat(),
            "pcWentOff": interrupted.pc_went_off.isoformat() if interrupted.pc_went_off else None,
        } if interrupted else None,
        "pcOnSince": this_boot.on.isoformat() if this_boot else None,
        "weeks": [
            {
                "start": week.start.isoformat(),
                "end": week.end.isoformat(),
                "worked": minutes(week.worked),
                "overtime": minutes(week.overtime),
                "running": week.end >= now.date(),
            }
            for week in reversed(all_weeks)
        ],
        "shifts": [_shift(shift, sessions, rules, now) for shift in reversed(all_shifts)],
        "labels": labels(all_shifts),
        "days": {
            day.date.isoformat(): {"late": minutes(day.late), "short": minutes(day.short), "madeUp": day.made_up, "lastOut": day.last_out.isoformat()}
            for week in all_weeks for day in week.days if day.late > timedelta()
        },
        "byLabel": {
            "week": _by_label([s for s in completed(all_shifts) if s.start.date() >= now.date() - timedelta(days=now.weekday())], rules),
            "all": _by_label(completed(all_shifts), rules),
        },
        "periods": [
            {
                "start": period.start.isoformat(),
                "end": period.end.isoformat(),
                "owed": minutes(period.owed),
                "paid": minutes(period.paid),
                "timeOff": minutes(period.time_off),
                "shortfall": minutes(period.shortfall),
                "references": list(period.references),
            }
            for period in reversed(reconciliation.periods)
        ],
        "unmatched": [{"date": day.date.isoformat(), "overtime": minutes(day.overtime)} for day in reconciliation.unmatched],
        "totals": {
            "owed": minutes(reconciliation.owed),
            "compensated": minutes(reconciliation.compensated),
            "shortfall": minutes(reconciliation.shortfall),
            "unmatched": minutes(reconciliation.unmatched_overtime),
        },
        "integrity": {"entries": len(sheet.ledger.entries()), "problems": sheet.problems(include_history=False)},
        "saving": _saving(sheet),
        "setup": {
            "needed": not rules.configured,
            "lunch": f"{rules.lunch_start:%H:%M} for {rules.lunch_minutes} min",
            "shift": f"{rules.shift_start:%H:%M} to {rules.shift_end:%H:%M}",
            "lunchQuestion": setup.LUNCH_QUESTION,
            "shiftQuestion": setup.SHIFT_QUESTION,
        },
        "rules": {
            "lunchStart": f"{rules.lunch_start:%H:%M}",
            "lunchMinutes": rules.lunch_minutes,
            "dailyHours": rules.daily_hours,
            "weeklyHours": rules.weekly_hours,
            "daysOff": [DAY_NAMES[day] for day in range(7) if day not in rules.workdays],
        },
    }


def _shift(shift: Shift, sessions: list[PcSession], rules: Rules, now: datetime) -> dict:
    backing = support(shift.start, shift.end, sessions, now)
    return {
        "pc": {
            "share": round(backing.share, 3),
            "beforeRecords": backing.before_records,
            "sessions": [
                {"on": s.on.isoformat(), "off": s.off.isoformat() if s.off else None, "exact": s.exact} for s in backing.sessions
            ],
        },
        "id": shift.id,
        "label": shift.label,
        "start": shift.start.isoformat(),
        "end": shift.end.isoformat() if shift.end else None,
        "worked": minutes(rules.worked(shift.segments(now))) if shift.end else None,
        "lunch": minutes(rules.lunch_taken(shift.segments(now))),
        "voided": shift.voided,
        "lateBy": minutes(shift.entered_late_by) if shift.entered_late_by > LATE_ENOUGH_TO_FLAG else None,
        "notes": shift.notes,
        "changes": shift.changes,
    }


def _by_label(chosen: list[Shift], rules: Rules) -> list[dict]:
    return [{"label": label, "worked": minutes(worked)} for label, worked in worked_by_label(chosen, rules).items()]


def _saving(sheet: Timesheet) -> dict:
    book = sheet.publish.book if sheet.publish else None
    history = book.history() if book else {}
    stamps = timestamps.stamps(sheet.directory)
    latest = max((s.seq for s in stamps), default=None)
    return {
        "kinds": places.KINDS,
        "places": [
            {
                "id": place.id,
                "kind": place.kind,
                "kindLabel": places.KINDS[place.kind],
                "name": place.name,
                "target": place.target,
                "saved": history.get(place.id, {}).get("saved"),
                "error": history.get(place.id, {}).get("error"),
            }
            for place in (book.places() if book else [])
        ],
        "stamped": {
            "upTo": latest,
            "by": [{"authority": s.authority_name, "time": s.time.isoformat()} for s in stamps if s.seq == latest],
        },
    }
