from chronata.timekeeping.labels import LabelChoice, choose, known_labels, suggested, tidy
from chronata.timekeeping.entries.labels import ShiftLabelled
from chronata.timekeeping.shifts import Shift
from chronata.timekeeping.working_day import WorkingDay
from chronata.use_cases.log import Log, one_writer_at_a_time
from chronata.use_cases import typed_input
from chronata.use_cases.outcome import LabelNeedsHours, Outcome, UnconfirmedLabel, UserError


class Labelling:
    def __init__(self, log: Log):
        self.log = log

    @one_writer_at_a_time
    def label_shift(self, shift_id: int, label: str, new_label: bool = False) -> Outcome:
        shift = self.log.shift(shift_id)
        label = self.settle(label, new_label, self.in_use(self.log.shifts()), needs_hours=True)
        if shift.label == label:
            raise UserError(f"shift {shift_id} is already labelled {label or 'with nothing'}")
        return self.log.write(ShiftLabelled(shift.id, label), f"labelled shift {shift.id} {label or '(no label)'}", self.log.clock())

    @one_writer_at_a_time
    def rename(self, old: str, new: str, new_label: bool = False) -> Outcome:
        all_shifts = self.log.shifts()
        known = known_labels(all_shifts)
        current = choose(old, known)
        if not current.label or not current.exists:
            raise UserError(f"there is no label '{old.strip()}'")
        others = [shift for shift in all_shifts if shift.label != current.label]
        target = self.settle(new, new_label, known_labels(others)) if _key_differs(new, current.label) else tidy(new)
        if not target:
            raise UserError("give the new name for the label")
        if target == current.label:
            raise UserError(f"the label is already called {target}")
        affected = [shift for shift in all_shifts if shift.label == current.label]
        now = self.log.clock()
        for shift in affected:
            self.log.append(ShiftLabelled(shift.id, target, f"label renamed from {current.label}"), now)
        merged = target in known
        message = (f"merged {current.label} into {target}" if merged else f"renamed label {current.label} to {target}") + f" on {len(affected)} shift{'s' if len(affected) != 1 else ''}"
        self.log.label_hours.rename(current.label, target)
        if self.log.hours.default_label == current.label:
            self.log.label_hours.save_default_label(target)
            message += f"; {target} is now the default"
        return self.log.commit(message)

    @one_writer_at_a_time
    def set_default(self, label: str, new_label: bool = False) -> Outcome:
        chosen = self.settle(label, new_label, self.in_use(self.log.shifts()), needs_hours=True)
        changed = self.adopt_default(chosen)
        if changed is None:
            raise UserError(f"{chosen} is already the default" if chosen else "there is no default label to clear")
        return self.log.commit(changed)

    @one_writer_at_a_time
    def create(self, name: str, shift_answer: str, lunch_answer: str, no_set_hours: bool = False, new_label: bool = False) -> Outcome:
        label = self.settle(name, new_label, self.in_use(self.log.shifts()))
        if not label:
            raise UserError("give the new label a name")
        if label in self.in_use(self.log.shifts()):
            raise UserError(f"{label} already exists; change its hours instead")
        hours = None if no_set_hours else typed_input.hours(shift_answer, lunch_answer)
        self.log.label_hours.save_hours(label, hours)
        return self.log.commit(f"added label {label} with {describe_hours(hours)}")

    def adopt_default(self, chosen: str) -> str | None:
        if chosen == self.log.hours.default_label:
            return None
        self.log.label_hours.save_default_label(chosen)
        return f"made {chosen} the default label" if chosen else "cleared the default label"

    def suggested(self) -> str:
        return suggested(self.log.shifts(), self.log.clock(), self.log.hours.default_label)

    def check(self, typed: str) -> LabelChoice:
        return choose(typed, self.in_use(self.log.shifts()))

    def in_use(self, all_shifts: list[Shift]) -> list[str]:
        hours = self.log.hours
        named = [hours.default_label, *hours.labels()]
        return list(dict.fromkeys(known_labels(all_shifts) + [label for label in named if label]))

    def settle(self, typed: str | None, confirmed_new: bool, known: list[str], needs_hours: bool = False) -> str:
        choice = choose(typed or "", known)
        if not choice.exists and choice.near_misses and not confirmed_new:
            raise UnconfirmedLabel(choice.label, choice.near_misses)
        if needs_hours and not choice.exists:
            raise LabelNeedsHours(choice.label)
        return choice.label


def describe_hours(hours: WorkingDay | None) -> str:
    if hours is None:
        return "no set hours"
    lunch = f"lunch at {hours.lunch.start:%H:%M} for {hours.lunch.minutes} min" if hours.lunch else "no lunch"
    return f"shift {hours.shift_start:%H:%M}–{hours.shift_end:%H:%M}, {lunch}"


def _key_differs(typed: str, label: str) -> bool:
    return tidy(typed).casefold() != label.casefold()
