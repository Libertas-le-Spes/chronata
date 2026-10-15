from chronata.timekeeping.labels import LabelChoice, choose, known_labels, suggested, tidy
from chronata.timekeeping.shifts import Shift
from chronata.use_cases.log import Log, one_writer_at_a_time
from chronata.use_cases.outcome import Outcome, UnconfirmedLabel, UserError


class Labelling:
    def __init__(self, log: Log):
        self.log = log

    @one_writer_at_a_time
    def label_shift(self, shift_id: int, label: str, new_label: bool = False) -> Outcome:
        shift = self.log.shift(shift_id)
        label = self.settle(label, new_label, self.in_use(self.log.shifts()))
        if shift.label == label:
            raise UserError(f"shift {shift_id} is already labelled {label or 'with nothing'}")
        return self.log.write("shift_labelled", {"shift": shift.id, "label": label}, f"labelled shift {shift.id} {label or '(no label)'}", self.log.clock())

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
            self.log.record.append("shift_labelled", {"shift": shift.id, "label": target, "reason": f"label renamed from {current.label}"}, now)
        merged = target in known
        message = (f"merged {current.label} into {target}" if merged else f"renamed label {current.label} to {target}") + f" on {len(affected)} shift{'s' if len(affected) != 1 else ''}"
        if self.log.working_day.default_label == current.label:
            self.log.working_days.save_default_label(target)
            message += f"; {target} is now the default"
        return self.log.commit(message)

    @one_writer_at_a_time
    def set_default(self, label: str, new_label: bool = False) -> Outcome:
        chosen = self.settle(label, new_label, self.in_use(self.log.shifts()))
        changed = self.adopt_default(chosen)
        if changed is None:
            raise UserError(f"{chosen} is already the default" if chosen else "there is no default label to clear")
        return self.log.commit(changed)

    def adopt_default(self, chosen: str) -> str | None:
        if chosen == self.log.working_day.default_label:
            return None
        self.log.working_days.save_default_label(chosen)
        return f"made {chosen} the default label" if chosen else "cleared the default label"

    def suggested(self) -> str:
        return suggested(self.log.shifts(), self.log.clock(), self.log.working_day.default_label)

    def check(self, typed: str) -> LabelChoice:
        return choose(typed, self.in_use(self.log.shifts()))

    def in_use(self, all_shifts: list[Shift]) -> list[str]:
        known = known_labels(all_shifts)
        default = self.log.working_day.default_label
        return known + [default] if default and default not in known else known

    def settle(self, typed: str | None, confirmed_new: bool, known: list[str]) -> str:
        choice = choose(typed or "", known)
        if not choice.exists and choice.near_misses and not confirmed_new:
            raise UnconfirmedLabel(choice.label, choice.near_misses)
        return choice.label


def _key_differs(typed: str, label: str) -> bool:
    return tidy(typed).casefold() != label.casefold()
