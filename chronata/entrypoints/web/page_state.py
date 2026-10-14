from dataclasses import replace
from datetime import date, datetime, timedelta

from chronata.presenters.readable_copy import label_folder
from chronata.presenters.text_report import LATE_ENOUGH_TO_FLAG
from chronata.timekeeping.durations import minutes
from chronata.timekeeping.pc_sessions import PcSession, support
from chronata.timekeeping.labels import hours_by_label, known_labels
from chronata.timekeeping.shifts import Shift, completed, open_shift
from chronata.timekeeping.working_day import WEEKDAY_NAMES, Week, WorkingDay, weeks
from chronata.use_cases import typed_input


def page_state(app) -> dict:
    sheet = app.sheet
    now = sheet.clock()
    working_day = sheet.working_day
    all_shifts = sheet.shifts()
    all_weeks = sheet.weeks()
    reconciliation = sheet.reconciliation(all_weeks)
    current = open_shift(all_shifts)
    sessions = sheet.pc_sessions()
    this_boot = sheet.this_boot()
    interrupted = sheet.interrupted()
    return {
        "now": now.isoformat(),
        "open": {"id": current.id, "start": current.start.isoformat(), "workedSeconds": round(current.worked(now).total_seconds())} if current else None,
        "interrupted": {
            "start": interrupted.shift.start.isoformat(),
            "pcWentOff": interrupted.pc_went_off.isoformat() if interrupted.pc_went_off else None,
        } if interrupted else None,
        "pcOnSince": this_boot.on.isoformat() if this_boot else None,
        "beforeEndOfWorkday": working_day.before_end_of_workday(now),
        "shiftEnd": f"{working_day.shift_end:%H:%M}",
        "weeks": [
            {"start": week.start.isoformat(), "end": week.end.isoformat(), "worked": minutes(week.worked),
             "overtime": minutes(week.overtime), "running": week.end >= now.date()}
            for week in reversed(all_weeks)
        ],
        "shifts": [_shift(shift, sessions, now) for shift in reversed(all_shifts)],
        "unexplainedBreaks": [
            {"shift": shift.id, "start": gap.start.isoformat(), "end": gap.end.isoformat()}
            for shift in all_shifts for gap in shift.breaks if gap.cause == "PC off" and not gap.reason
        ],
        "labels": known_labels(all_shifts),
        "chart": _chart(all_shifts, working_day, now, running=None if interrupted else current),
        "days": {
            day.date.isoformat(): {"late": minutes(day.late), "short": minutes(day.short), "madeUp": day.made_up, "lastOut": day.last_out.isoformat()}
            for week in all_weeks for day in week.days if day.late > timedelta() or day.short > timedelta()
        },
        "labelSummary": _label_summary(all_shifts, now),
        "periods": [
            {"start": period.start.isoformat(), "end": period.end.isoformat(), "owed": minutes(period.owed),
             "paid": minutes(period.paid), "timeOff": minutes(period.time_off), "shortfall": minutes(period.shortfall),
             "references": list(period.references)}
            for period in reversed(reconciliation.periods)
        ],
        "unmatched": [{"date": day.date.isoformat(), "overtime": minutes(day.overtime)} for day in reconciliation.unmatched],
        "totals": {
            "owed": minutes(reconciliation.owed),
            "compensated": minutes(reconciliation.compensated),
            "shortfall": minutes(reconciliation.shortfall),
            "unmatched": minutes(reconciliation.unmatched_overtime),
        },
        "integrity": {"entries": sheet.entry_count(), "problems": sheet.problems()},
        "saving": _saving(app),
        "setup": {
            "needed": not working_day.configured,
            "lunch": f"{working_day.lunch_start:%H:%M} for {working_day.lunch_minutes} min",
            "shift": f"{working_day.shift_start:%H:%M} to {working_day.shift_end:%H:%M}",
            "lunchQuestion": typed_input.LUNCH_QUESTION,
            "shiftQuestion": typed_input.SHIFT_QUESTION,
        },
        "workingDay": {
            "dailyHours": working_day.daily_hours,
            "weeklyHours": working_day.weekly_hours,
            "daysOff": [WEEKDAY_NAMES[day] for day in range(7) if day not in working_day.workdays],
        },
    }


def _shift(shift: Shift, sessions: list[PcSession], now: datetime) -> dict:
    backing = support(shift.start, shift.end, sessions, now)
    return {
        "id": shift.id,
        "label": shift.label,
        "start": shift.start.isoformat(),
        "end": shift.end.isoformat() if shift.end else None,
        "since": shift.since.isoformat(),
        "worked": minutes(shift.worked(now)),
        "voided": shift.voided,
        "lateBy": minutes(shift.entered_late_by) if shift.entered_late_by > LATE_ENOUGH_TO_FLAG else None,
        "notes": shift.notes,
        "changes": shift.changes,
        "pc": {
            "share": round(backing.share, 3),
            "beforeRecords": backing.before_records,
            "sessions": [{"on": s.on.isoformat(), "off": s.off.isoformat() if s.off else None, "exact": s.exact} for s in backing.sessions],
        },
    }


def _chart(all_shifts: list[Shift], working_day: WorkingDay, now: datetime, running: Shift | None) -> dict:
    counted = completed(all_shifts) + ([replace(running, end=now)] if running else [])
    recent: dict[date, Week | None] = {week.start: week for week in weeks(counted, working_day)[-8:]}
    recent.setdefault(now.date() - timedelta(days=now.weekday()), None)
    return {
        "targetMinutes": round(working_day.daily_hours * 60),
        "weeks": [
            {"start": start.isoformat(), "days": [_chart_day(start + timedelta(days=i), week, now, running) for i in range(7)]}
            for start, week in sorted(recent.items())
        ],
    }


def _chart_day(day: date, week: Week | None, now: datetime, running: Shift | None) -> dict:
    found = next((d for d in week.days if d.date == day), None) if week else None
    return {
        "date": day.isoformat(),
        "normal": minutes(found.worked - found.overtime) if found else 0,
        "overtime": minutes(found.overtime) if found else 0,
        "late": minutes(found.late) if found else 0,
        "short": minutes(found.short) if found else 0,
        "madeUp": bool(found and found.made_up),
        "soFar": bool(running) and day == now.date(),
        "future": day > now.date(),
    }


def _label_summary(all_shifts: list[Shift], now: datetime) -> list[dict]:
    return [{"label": row.label, "folder": label_folder(row.label), "week": minutes(row.this_week), "all": minutes(row.all_time), "openNow": row.open_now}
            for row in hours_by_label(all_shifts, now)]


def _saving(app) -> dict:
    kinds = app.saving.places.kinds()
    newest, by = app.saving.stamped()
    return {
        "kinds": kinds,
        "places": [
            {"id": place.id, "kind": place.kind, "kindLabel": kinds[place.kind], "name": place.name, "target": place.target,
             "saved": last.get("saved"), "error": last.get("error")}
            for place, last in app.saving.statuses()
        ],
        "stamped": {"upTo": newest, "by": [{"authority": s.authority_name, "time": s.time.isoformat()} for s in by]},
    }
