from time import sleep
from datetime import date, datetime, timedelta

from chronata.timekeeping.shifts import completed, open_shift, unexplained_pc_breaks
from chronata.use_cases.outcome import UserError
from chronata.use_cases.ports import Desktop
from chronata.use_cases.timesheet import Timesheet

REMINDER_HOURS = range(7, 18)
BETWEEN_REMINDERS = timedelta(hours=1)
REMINDERS_PER_DAY = 2
LONG_SHIFT = timedelta(hours=12)


class Reminders:
    def __init__(self, sheet: Timesheet, desktop: Desktop, page_url: str):
        self.sheet = sheet
        self.desktop = desktop
        self.page_url = page_url
        self.clock_in_reminders: dict[date, list[datetime]] = {}
        self.lunch_asked: set[date] = set()
        self.lunch_return_asked: set[date] = set()
        self.long_shift_warned: set[int] = set()

    def on_login(self) -> None:
        self.sheet.record_pc_sessions()
        if not self.sheet.working_day.configured:
            self.desktop.notify("Set your working day", "Two questions: when lunch is, and your shift hours. Click to answer.",
                                self._open("setup"), click_label="Set up")
        for _, gap in unexplained_pc_breaks(self.sheet.shifts(), self.sheet.clock().date()):
            self.desktop.notify(f"Your PC was off {gap.start:%H:%M}–{gap.end:%H:%M}",
                                "That time isn't counted as work. Click to say why, for the record.",
                                self._open("explain-break"), click_label="Say why")
        interrupted = self.sheet.interrupted()
        if interrupted is None:
            return
        if interrupted.pc_went_off is None:
            self.desktop.notify("Last shift is still open", f"Started {interrupted.shift.start:%a %d %b %H:%M}. Click to open the log and close it.",
                                self._open(""))
            return
        went_off = interrupted.pc_went_off
        self.desktop.notify(
            "You were clocked in when the PC turned off",
            f"Shift from {interrupted.shift.start:%a %H:%M}. The PC turned off {went_off:%a %H:%M}. Click to clock out at that time.",
            lambda: self._clock_out(went_off.isoformat(), "clocked out at the time the PC turned off"),
            click_label="Clock out at that time",
        )

    def tick(self) -> None:
        now = self.sheet.clock()
        all_shifts = self.sheet.shifts()
        current = open_shift(all_shifts)
        lunch_starts, lunch_ends = self.sheet.working_day.lunch_on(now.date(), now.tzinfo)
        if current:
            if lunch_starts <= now < lunch_ends and now.date() not in self.lunch_asked:
                self.lunch_asked.add(now.date())
                self.desktop.notify("Lunch time", "Clocking out for lunch? Ignore this if you're working through it.",
                                    lambda: self._clock_out(None, "lunch"), click_label="Clock out for lunch")
            if now - current.since >= LONG_SHIFT and current.id not in self.long_shift_warned:
                self.long_shift_warned.add(current.id)
                self.desktop.notify("Still working?", f"Clocked in since {current.start:%H:%M}. Click to open the log.", self._open(""))
            return
        finished_today = [s for s in completed(all_shifts) if s.start.date() == now.date()]
        out_for_lunch = any(lunch_starts <= s.end < lunch_ends for s in finished_today)
        if out_for_lunch and now >= lunch_ends and now.date() not in self.lunch_return_asked:
            self.lunch_return_asked.add(now.date())
            self.desktop.notify("Lunch is over", "Clocking back in?", lambda: self._clock_in("back from lunch"), click_label="Clock back in")
            return
        if now.hour not in REMINDER_HOURS or finished_today:
            return
        sent = self.clock_in_reminders.setdefault(now.date(), [])
        if len(sent) >= REMINDERS_PER_DAY or (sent and now - sent[-1] < BETWEEN_REMINDERS):
            return
        sent.append(now)
        if now.weekday() in self.sheet.working_day.workdays:
            self.desktop.notify("Not clocked in", "If you've started work, click to clock in now.",
                                lambda: self._clock_in("clocked in from the reminder"), click_label="Clock in")
        else:
            self.desktop.notify(f"It's {now:%A}. Working today?", "Your PC is on. If you're working, click to clock in now.",
                                lambda: self._clock_in("clocked in from the reminder"), click_label="Clock in")

    def run_forever(self) -> None:
        self.on_login()
        while True:
            self.tick()
            sleep(60)

    def _open(self, section: str):
        return lambda: self.desktop.open_page(self.page_url + (f"#{section}" if section else ""))

    def _clock_in(self, note: str) -> None:
        try:
            outcome = self.sheet.clock_in(None, note)
            self.desktop.notify(outcome.message.capitalize(), outcome.warning or "")
        except UserError as error:
            self.desktop.notify("Could not clock in", str(error))

    def _clock_out(self, at: str | None, note: str) -> None:
        try:
            outcome = self.sheet.clock_out(at, note)
            self.desktop.notify(outcome.message.capitalize(), outcome.warning or "")
        except UserError as error:
            self.desktop.notify("Could not clock out", str(error))
