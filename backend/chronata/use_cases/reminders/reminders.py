from time import sleep

from chronata.timekeeping.shifts.shifts import completed, open_shift
from chronata.use_cases.clocking.clocking import Clocking
from chronata.use_cases.log.log import Log
from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.log.ports import Desktop, Page
from chronata.use_cases.pc.pc_records import PcRecords
from chronata.use_cases.reminders.at_login import NeedsSetUp, PcOffUnexplained, ShiftLeftOpen
from chronata.use_cases.reminders.during_the_day import LongShift, LunchOver, LunchTime, NotClockedIn
from chronata.use_cases.reminders.situation import Actions, Nudge, Situation


class Reminders:
    def __init__(self, log: Log, clocking: Clocking, pc: PcRecords, desktop: Desktop, page: Page):
        self.log = log
        self.clocking = clocking
        self.pc = pc
        self.desktop = desktop
        self.page = page
        self.at_login = [NeedsSetUp(), PcOffUnexplained(), ShiftLeftOpen()]
        self.during_the_day = [LunchTime(), LongShift(), LunchOver(), NotClockedIn()]
        self.actions = Actions(self._clock_in, self._clock_out, self._open)

    def on_login(self) -> None:
        self.pc.record_sessions()
        situation, shifts, interrupted = self._situation(), self.log.shifts(), self.pc.interrupted()
        for nudge in (nudge for kind in self.at_login for nudge in kind.notices(situation, shifts, interrupted)):
            self._show(nudge)

    def tick(self) -> None:
        situation = self._situation()
        for nudge in filter(None, (kind.due(situation) for kind in self.during_the_day)):
            self._show(nudge)

    def run_forever(self) -> None:
        self.on_login()
        while True:
            self.tick()
            sleep(60)

    def _situation(self) -> Situation:
        now = self.log.clock()
        all_shifts = self.log.shifts()
        finished_today = [shift for shift in completed(all_shifts) if shift.start.date() == now.date()]
        return Situation(now, open_shift(all_shifts), finished_today, self.log.hours, self.actions)

    def _show(self, nudge: Nudge) -> None:
        self.desktop.notify(nudge.summary, nudge.body, nudge.on_click, click_label=nudge.click_label)

    def _open(self, section: str) -> None:
        self.page.open(section)

    def _clock_in(self, note: str) -> None:
        self._report("Could not clock in", lambda: self.clocking.clock_in(None, note))

    def _clock_out(self, at: str | None, note: str) -> None:
        self._report("Could not clock out", lambda: self.clocking.clock_out(at, note))

    def _report(self, failure: str, change) -> None:
        try:
            outcome = change()
        except UserError as error:
            self.desktop.notify(failure, str(error))
            return
        self.desktop.notify(outcome.headline, outcome.warning or "")
