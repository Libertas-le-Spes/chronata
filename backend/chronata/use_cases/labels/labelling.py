from chronata.timekeeping.entries.labels import ShiftLabelled
from chronata.timekeeping.hours.working_day import WorkingDay
from chronata.timekeeping.labels.labels import LabelChoice, choose, known_labels, suggested, tidy
from chronata.timekeeping.shifts.shifts import Shift, named
from chronata.use_cases.log.log import Log, one_writer_at_a_time
from chronata.use_cases.log.outcome import Outcome, UserError
from chronata.use_cases.questions import typed_input
from chronata.use_cases.questions.questions import Answers, LabelNeedsHours, UnconfirmedLabel


class Labelling:
    def __init__(self, log: Log):
        self.log = log

    @one_writer_at_a_time
    def label_shifts(self, shift_ids: list[int], label: str, answers: Answers = Answers()) -> Outcome:
        chosen_shifts = self.log.shifts_with(shift_ids)
        label = self.settle(label, self.in_use(self.log.shifts()), answers, needs_hours=True)
        changing = [shift for shift in chosen_shifts if shift.label != label]
        if not changing:
            raise UserError(f"{named(chosen_shifts)} already labelled {label or 'with nothing'}")
        now = self.log.clock()
        for shift in changing:
            self.log.append(ShiftLabelled(shift.id, label), now)
        return self.log.commit(f"labelled {named(changing)} {label or '(no label)'}")

    @one_writer_at_a_time
    def rename(self, old: str, new: str, answers: Answers = Answers()) -> Outcome:
        all_shifts = self.log.shifts()
        current = self._existing(old, all_shifts)
        target = self._new_name(new, current, all_shifts, answers)
        affected = [shift for shift in all_shifts if shift.label == current]
        now = self.log.clock()
        for shift in affected:
            self.log.append(ShiftLabelled(shift.id, target, f"label renamed from {current}"), now)
        merged = target in self.in_use(all_shifts)
        message = (f"merged {current} into {target}" if merged else f"renamed label {current} to {target}") + f" on {len(affected)} shift{'s' if len(affected) != 1 else ''}"
        return self.log.commit(message + self._carry_hours_and_default(current, target))

    def _existing(self, old: str, all_shifts: list[Shift]) -> str:
        current = choose(old, self.in_use(all_shifts))
        if not current.label or not current.exists:
            raise UserError(f"there is no label '{old.strip()}'")
        return current.label

    def _new_name(self, new: str, current: str, all_shifts: list[Shift], answers: Answers) -> str:
        others = [label for label in self.in_use(all_shifts) if label != current]
        target = self.settle(new, others, answers) if _key_differs(new, current) else tidy(new)
        if not target:
            raise UserError("give the new name for the label")
        if target == current:
            raise UserError(f"the label is already called {target}")
        return target

    def _carry_hours_and_default(self, current: str, target: str) -> str:
        self.log.label_hours.rename(current, target)
        if self.log.hours.default_label != current:
            return ""
        self.log.label_hours.save_default_label(target)
        return f"; {target} is now the default"

    @one_writer_at_a_time
    def set_default(self, label: str, answers: Answers = Answers()) -> Outcome:
        chosen = self.settle(label, self.in_use(self.log.shifts()), answers, needs_hours=True)
        changed = self.adopt_default(chosen)
        if changed is None:
            raise UserError(f"{chosen} is already the default" if chosen else "there is no default label to clear")
        return self.log.commit(changed)

    @one_writer_at_a_time
    def create(self, name: str, answers: Answers) -> Outcome:
        label = self.settle(name, self.in_use(self.log.shifts()), answers)
        if not label:
            raise UserError("give the new label a name")
        if label in self.in_use(self.log.shifts()):
            raise UserError(f"{label} already exists; change its hours instead")
        return self.log.commit(self._add(label, answers))

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

    def settle(self, typed: str | None, known: list[str], answers: Answers, needs_hours: bool = False) -> str:
        choice = choose(typed or "", known)
        if _looks_like_another(choice, answers):
            raise UnconfirmedLabel(choice.label, choice.near_misses)
        if needs_hours and not choice.exists:
            if not answers.gave_hours:
                raise LabelNeedsHours(choice.label)
            self.log.history.commit(self._add(choice.label, answers))
        return choice.label

    def _add(self, label: str, answers: Answers) -> str:
        hours = None if answers.no_set_hours else typed_input.hours(answers.shift, answers.lunch)
        self.log.label_hours.save_hours(label, hours)
        return f"added label {label} with {describe_hours(hours)}"


def describe_hours(hours: WorkingDay | None) -> str:
    if hours is None:
        return "no set hours"
    lunch = f"lunch at {hours.lunch.start:%H:%M} for {hours.lunch.minutes} min" if hours.lunch else "no lunch"
    return f"shift {hours.shift_start:%H:%M}–{hours.shift_end:%H:%M}, {lunch}"


def _looks_like_another(choice: LabelChoice, answers: Answers) -> bool:
    if choice.exists or answers.new_label:
        return False
    return bool(choice.near_misses)


def _key_differs(typed: str, label: str) -> bool:
    return tidy(typed).casefold() != label.casefold()
