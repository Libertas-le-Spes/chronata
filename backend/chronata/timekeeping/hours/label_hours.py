from dataclasses import dataclass, field
from datetime import datetime

from chronata.timekeeping.hours.working_day import MONDAY_TO_FRIDAY, WorkingDay


@dataclass(frozen=True)
class LabelHours:
    default_label: str = ""
    by_label: dict[str, WorkingDay | None] = field(default_factory=dict)

    @property
    def configured(self) -> bool:
        return bool(self.by_label)

    @property
    def main(self) -> WorkingDay | None:
        return self.for_label(self.default_label)

    def for_label(self, label: str) -> WorkingDay | None:
        return self.by_label.get(self.counted_under(label))

    def counted_under(self, label: str) -> str:
        if label:
            return label
        return self.default_label

    def labels(self) -> list[str]:
        named = []
        for label in self.by_label:
            if label:
                named.append(label)
        return named

    def is_workday(self, moment: datetime) -> bool:
        return moment.weekday() in self._main_workdays()

    def _main_workdays(self) -> frozenset[int]:
        if self.main is None:
            return MONDAY_TO_FRIDAY
        return self.main.workdays

    def strays_from_default(self, label: str, moment: datetime) -> bool:
        if not self.default_label or label == self.default_label:
            return False
        return self.is_workday(moment)

    def before_end_of_workday(self, label: str, moment: datetime) -> bool:
        hours = self.for_label(label)
        return hours is not None and hours.before_end_of_workday(moment)
