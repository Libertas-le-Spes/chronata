from chronata.timekeeping.shifts.today import unexplained_pc_breaks
from chronata.use_cases.pc.pc_records import Interrupted
from chronata.use_cases.reminders.situation import Nudge, Situation


class NeedsSetUp:
    def notices(self, situation: Situation, shifts: list, interrupted: Interrupted | None) -> list[Nudge]:
        if situation.hours.configured:
            return []
        return [Nudge("Set your working day", "Your shift hours, and lunch if you take one. Click to answer.", situation.actions.open("setup"), "Set up")]


class PcOffUnexplained:
    def notices(self, situation: Situation, shifts: list, interrupted: Interrupted | None) -> list[Nudge]:
        return [Nudge(f"Your PC was off {gap.start:%H:%M}–{gap.end:%H:%M}", "That time isn't counted as work. Click to say why, for the record.",
                      situation.actions.open("explain-break"), "Say why")
                for _, gap in unexplained_pc_breaks(shifts, situation.now.date())]


class ShiftLeftOpen:
    def notices(self, situation: Situation, shifts: list, interrupted: Interrupted | None) -> list[Nudge]:
        if interrupted is None:
            return []
        went_off = interrupted.pc_went_off
        if went_off is None:
            return [Nudge("Last shift is still open", f"Started {interrupted.shift.start:%a %d %b %H:%M}. Click to open the log and close it.",
                          situation.actions.open())]
        return [Nudge("You were clocked in when the PC turned off",
                      f"Shift from {interrupted.shift.start:%a %H:%M}. The PC turned off {went_off:%a %H:%M}. Click to clock out at that time.",
                      situation.actions.clock_out(went_off.isoformat(), "clocked out at the time the PC turned off"), "Clock out at that time")]
