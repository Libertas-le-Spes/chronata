import time
from datetime import date, datetime, timedelta

from chronata.desktop import notify, open_page
from chronata.shifts import completed, open_shift
from chronata.timesheet import Timesheet, UserError

REMINDER_HOURS = range(7, 18)
BETWEEN_REMINDERS = timedelta(hours=1)
REMINDERS_PER_DAY = 2
LONG_SHIFT = timedelta(hours=12)


class Nudges:
    def __init__(self, sheet: Timesheet, page_url: str):
        self.sheet = sheet
        self.page_url = page_url
        self.reminded: dict[date, list[datetime]] = {}
        self.long_shift_warned: set[int] = set()

    def on_login(self) -> None:
        self.sheet.record_pc_sessions()
        if not self.sheet.rules.configured:
            notify("Set your working day", "Two questions: when lunch is, and your shift hours. Click to answer.",
                   lambda: open_page(self.page_url), click_label="Set up")
        interrupted = self.sheet.interrupted()
        if interrupted is None:
            return
        if interrupted.pc_went_off is None:
            notify("Last shift is still open", f"Started {interrupted.shift.start:%a %d %b %H:%M}. Click to open the log and close it.",
                   lambda: open_page(self.page_url))
            return
        went_off = interrupted.pc_went_off
        notify(
            "You were clocked in when the PC turned off",
            f"Shift from {interrupted.shift.start:%a %H:%M}. The PC's last activity was {went_off:%a %H:%M}. Click to clock out at that time.",
            lambda: self._clock_out_at(went_off),
            click_label="Clock out at that time",
        )

    def tick(self) -> None:
        now = self.sheet.clock()
        all_shifts = self.sheet.shifts()
        current = open_shift(all_shifts)
        if current:
            if now - current.start >= LONG_SHIFT and current.id not in self.long_shift_warned:
                self.long_shift_warned.add(current.id)
                notify("Still working?", f"Clocked in since {current.start:%H:%M}. Click to open the log.", lambda: open_page(self.page_url))
            return
        if now.hour not in REMINDER_HOURS:
            return
        if any(shift.start.date() == now.date() for shift in completed(all_shifts)):
            return
        sent = self.reminded.setdefault(now.date(), [])
        if len(sent) >= REMINDERS_PER_DAY or (sent and now - sent[-1] < BETWEEN_REMINDERS):
            return
        sent.append(now)
        if now.weekday() in self.sheet.rules.workdays:
            notify("Not clocked in", "If you've started work, click to clock in now.", self._clock_in, click_label="Clock in")
        else:
            notify(f"It's {now:%A}. Working today?", "Your PC is on. If you're working, click to clock in now.", self._clock_in, click_label="Clock in")

    def run_forever(self) -> None:
        self.on_login()
        while True:
            self.tick()
            time.sleep(60)

    def _clock_in(self) -> None:
        try:
            outcome = self.sheet.clock_in(None, "clocked in from the reminder")
            notify(outcome.message.capitalize(), outcome.warning or "")
        except UserError as error:
            notify("Could not clock in", str(error))

    def _clock_out_at(self, moment: datetime) -> None:
        try:
            outcome = self.sheet.clock_out(moment.isoformat(), "clocked out at the PC's last logged activity before it shut down")
            notify(outcome.message.capitalize(), outcome.warning or "")
        except UserError as error:
            notify("Could not clock out", str(error))
