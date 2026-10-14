import json
import subprocess
import tempfile
import unittest
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from chronata.audit_trail import AuditTrail
from chronata.journal import Boot
from chronata.pc_sessions import PcSession, support
from chronata import setup
from chronata.timesheet import Timesheet, UserError
from chronata.compensation import reconcile
from chronata.ledger import Entry, Ledger, TamperedLedger
from chronata.rules import Rules, weeks
from chronata.shifts import Shift

SAST = timezone(timedelta(hours=2))
def rules(lunch_minutes: int = 0, workdays: range = range(5), weekly_hours: float = 40) -> Rules:
    return Rules(time(8), time(16, 0) if not lunch_minutes else time(17), time(12), lunch_minutes, frozenset(workdays), weekly_hours, True)


MON_TO_FRI = rules()


def shift(day: str, start: str, end: str) -> Shift:
    begins = datetime.fromisoformat(f"{day}T{start}").replace(tzinfo=SAST)
    ends = datetime.fromisoformat(f"{day}T{end}").replace(tzinfo=SAST)
    return Shift(1, begins, ends, timedelta())


def paid(start: str, end: str, hours: float, kind: str = "paid") -> Entry:
    return Entry(1, "compensation", datetime.now(SAST), {"from": start, "to": end, "hours": hours, "kind": kind})


class OvertimeRules(unittest.TestCase):
    def test_hours_past_the_daily_limit_are_overtime(self):
        week = weeks([shift("2026-10-05", "08:00", "18:30")], MON_TO_FRI)[0]
        self.assertEqual(week.overtime, timedelta(hours=2, minutes=30))

    def test_every_hour_on_a_day_off_is_overtime(self):
        week = weeks([shift("2026-10-11", "10:00", "14:00")], MON_TO_FRI)[0]
        self.assertEqual(week.overtime, timedelta(hours=4))

    def test_hours_past_the_weekly_limit_are_overtime_even_within_daily_limits(self):
        six_day_week = rules(workdays=range(6))
        days = [shift(f"2026-10-{d:02d}", "08:00", "16:00") for d in range(5, 11)]
        week = weeks(days, six_day_week)[0]
        self.assertEqual(week.overtime, timedelta(hours=8))
        self.assertEqual(week.days[-1].overtime, timedelta(hours=8))

    def test_an_hour_is_never_counted_twice(self):
        days = [shift(f"2026-10-{d:02d}", "08:00", "18:00") for d in range(5, 10)]
        self.assertEqual(weeks(days, MON_TO_FRI)[0].overtime, timedelta(hours=10))


class Compensation(unittest.TestCase):
    def test_a_pay_period_ending_mid_week_takes_only_its_own_days(self):
        all_weeks = weeks([shift("2026-10-09", "08:00", "10:00"), shift("2026-10-10", "09:00", "12:00")], MON_TO_FRI)
        result = reconcile([paid("2026-09-26", "2026-10-09", 0)], all_weeks)
        self.assertEqual(result.periods[0].shortfall, NONE_HOURS)
        self.assertEqual([d.date for d in result.unmatched], [date(2026, 10, 10)])

    def test_unpaid_overtime_shows_as_a_shortfall(self):
        all_weeks = weeks([shift("2026-10-05", "08:00", "19:00")], MON_TO_FRI)
        result = reconcile([paid("2026-10-01", "2026-10-31", 1), paid("2026-10-01", "2026-10-31", 0.5, "time_off")], all_weeks)
        self.assertEqual(result.shortfall, timedelta(hours=1, minutes=30))


NONE_HOURS = timedelta()


class SealedLedger(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())
        self.ledger = Ledger(self.directory / "ledger.jsonl")
        for hour in (8, 17):
            self.ledger.append("clock_in", {"at": f"2026-10-05T{hour:02d}:00:00+02:00"}, datetime.now(SAST))

    def edit_first_line(self):
        lines = self.ledger.path.read_text().splitlines()
        record = json.loads(lines[0])
        record["data"]["at"] = "2026-10-05T06:00:00+02:00"
        self.ledger.path.write_text("\n".join([json.dumps(record), *lines[1:]]) + "\n")

    def test_an_untouched_ledger_verifies(self):
        self.assertEqual(self.ledger.verify(), [])

    def test_an_edited_line_is_caught(self):
        self.edit_first_line()
        self.assertIn("line 1: contents were changed after it was written", self.ledger.verify())

    def test_a_deleted_line_is_caught(self):
        lines = self.ledger.path.read_text().splitlines()
        self.ledger.path.write_text(lines[1] + "\n")
        self.assertTrue(self.ledger.verify())

    def test_nothing_can_be_appended_to_a_tampered_ledger(self):
        self.edit_first_line()
        with self.assertRaises(TamperedLedger):
            self.ledger.append("clock_in", {"at": "2026-10-06T08:00:00+02:00"}, datetime.now(SAST))


class GitHistory(unittest.TestCase):
    def test_rewriting_a_saved_line_shows_up_in_history(self):
        directory = Path(tempfile.mkdtemp())
        trail = AuditTrail(directory)
        trail.ensure()
        subprocess.run(["git", "-C", str(directory), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(directory), "config", "user.name", "test"], check=True)
        ledger = directory / "ledger.jsonl"
        ledger.write_text("first\n")
        trail.commit("one")
        ledger.write_text("first\nsecond\n")
        trail.commit("two")
        self.assertEqual(trail.rewrites("ledger.jsonl"), [])
        ledger.write_text("FIRST\nsecond\n")
        trail.commit("three")
        self.assertEqual(len(trail.rewrites("ledger.jsonl")), 1)


class Lunch(unittest.TestCase):
    with_lunch = rules(lunch_minutes=60)

    def test_a_normal_day_is_the_shift_less_lunch(self):
        self.assertEqual(self.with_lunch.daily_hours, 8)

    def test_lunch_comes_off_a_shift_that_spans_it(self):
        week = weeks([shift("2026-10-05", "08:00", "17:00")], self.with_lunch)[0]
        self.assertEqual((week.worked, week.overtime), (timedelta(hours=8), timedelta()))

    def test_clocking_out_for_lunch_does_not_take_it_off_twice(self):
        split = [shift("2026-10-05", "08:00", "12:00"), shift("2026-10-05", "13:00", "17:00")]
        self.assertEqual(weeks(split, self.with_lunch)[0].worked, timedelta(hours=8))

    def test_a_short_lunch_break_only_takes_off_the_part_worked(self):
        self.assertEqual(self.with_lunch.lunch_overlap(at("2026-10-05T12:30:00"), at("2026-10-05T18:00:00")), timedelta(minutes=30))


class SetupAnswers(unittest.TestCase):
    def test_blank_answers_take_the_defaults(self):
        self.assertEqual(setup.lunch(""), (time(12), 60))
        self.assertEqual(setup.shift(""), (time(8), time(17)))

    def test_the_ways_people_write_times(self):
        self.assertEqual(setup.lunch("12h30 for 45 min"), (time(12, 30), 45))
        self.assertEqual(setup.lunch("13:00 1h30"), (time(13), 90))
        self.assertEqual(setup.shift("08h00 to 17h00"), (time(8), time(17)))
        self.assertEqual(setup.shift("9am-5pm"), (time(9), time(17)))

    def test_nonsense_is_refused_with_a_reason(self):
        for bad in ("12:00", "lunch"):
            with self.assertRaises(ValueError):
                setup.lunch(bad)
        with self.assertRaises(ValueError):
            setup.shift("17:00 to 08:00")
        with self.assertRaises(ValueError):
            setup.check_fit(time(8), time(17), time(18), 60)


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=SAST)


class PcSupport(unittest.TestCase):
    sessions = [PcSession("a", at("2026-10-13T08:30:00"), at("2026-10-13T12:00:00")),
                PcSession("b", at("2026-10-13T13:00:00"), None)]

    def test_a_shift_inside_a_session_is_fully_supported(self):
        backing = support(at("2026-10-13T09:00:00"), at("2026-10-13T11:00:00"), self.sessions, at("2026-10-13T20:00:00"))
        self.assertEqual(backing.share, 1.0)

    def test_a_restart_in_the_middle_of_a_shift_leaves_a_gap(self):
        backing = support(at("2026-10-13T11:00:00"), at("2026-10-13T14:00:00"), self.sessions, at("2026-10-13T20:00:00"))
        self.assertAlmostEqual(backing.share, 2 / 3)
        self.assertEqual([s.boot for s in backing.sessions], ["a", "b"])

    def test_a_shift_before_any_pc_record_says_so(self):
        backing = support(at("2026-10-01T09:00:00"), at("2026-10-01T17:00:00"), self.sessions, at("2026-10-13T20:00:00"))
        self.assertTrue(backing.before_records)
        self.assertEqual(backing.sessions, ())


class RecordingPcSessions(unittest.TestCase):
    def setUp(self):
        self.now = at("2026-10-14T09:00:00")
        self.booted = "today"
        self.journal = [Boot("yesterday", at("2026-10-13T08:30:00"), at("2026-10-13T19:12:52"), False),
                        Boot("today", at("2026-10-14T08:29:56"), self.now, True)]
        directory = Path(tempfile.mkdtemp())
        self.sheet = Timesheet(directory, clock=lambda: self.now, boots=lambda: self.journal, boot_id=lambda: self.booted)
        for key, value in (("user.email", "test@example.com"), ("user.name", "test")):
            subprocess.run(["git", "-C", str(directory), "config", key, value], check=True)

    def test_each_session_is_recorded_once(self):
        self.sheet.record_pc_sessions()
        self.assertIsNone(self.sheet.record_pc_sessions())
        self.assertEqual([(s.boot, s.off) for s in self.sheet.pc_sessions()],
                         [("yesterday", at("2026-10-13T19:12:52")), ("today", None)])

    def test_the_off_time_is_filled_in_after_the_next_boot(self):
        self.sheet.record_pc_sessions()
        self.journal = [self.journal[0], Boot("today", at("2026-10-14T08:29:56"), at("2026-10-14T18:02:00"), False),
                        Boot("tomorrow", at("2026-10-15T08:00:00"), at("2026-10-15T08:00:00"), True)]
        self.booted = "tomorrow"
        self.sheet.record_pc_sessions()
        self.assertEqual(self.sheet.pc_sessions()[1].off, at("2026-10-14T18:02:00"))

    def test_a_shift_left_open_across_a_shutdown_offers_the_shutdown_time(self):
        self.booted = "yesterday"
        self.journal = [Boot("yesterday", at("2026-10-13T08:30:00"), at("2026-10-13T09:00:00"), True)]
        self.sheet.record_pc_sessions()
        self.now = at("2026-10-13T09:05:00")
        self.sheet.clock_in(None, None)
        self.assertIsNone(self.sheet.interrupted())

        self.journal = [Boot("yesterday", at("2026-10-13T08:30:00"), at("2026-10-13T19:12:52"), False),
                        Boot("today", at("2026-10-14T08:29:56"), at("2026-10-14T09:00:00"), True)]
        self.booted = "today"
        self.now = at("2026-10-14T09:00:00")
        self.sheet.record_pc_sessions()
        self.assertEqual(self.sheet.interrupted().pc_went_off, at("2026-10-13T19:12:52"))

    def test_an_exact_shutdown_time_is_kept_over_the_journal_guess(self):
        self.sheet.record_pc_sessions()
        self.now = at("2026-10-14T18:02:09")
        self.sheet.record_shutdown()
        self.journal = [self.journal[0], Boot("today", at("2026-10-14T08:29:56"), at("2026-10-14T18:02:15"), False),
                        Boot("tomorrow", at("2026-10-15T08:00:00"), at("2026-10-15T08:00:00"), True)]
        self.booted = "tomorrow"
        self.sheet.record_pc_sessions()
        today = self.sheet.pc_sessions()[1]
        self.assertEqual((today.off, today.exact), (at("2026-10-14T18:02:09"), True))

    def test_setup_answers_change_the_rules(self):
        self.assertFalse(self.sheet.rules.configured)
        self.sheet.configure("12h30 for 30 min", "07:30 to 16:00")
        self.assertEqual((self.sheet.rules.daily_hours, self.sheet.rules.configured), (8.0, True))
        with self.assertRaises(UserError):
            self.sheet.configure("12:00", "")


if __name__ == "__main__":
    unittest.main()
