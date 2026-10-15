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
        return self.by_label.get(label or self.default_label)

    def labels(self) -> list[str]:
        return [label for label in self.by_label if label]

    def is_workday(self, moment: datetime) -> bool:
        return moment.weekday() in (self.main.workdays if self.main else MONDAY_TO_FRIDAY)

    def strays_from_default(self, label: str, moment: datetime) -> bool:
        if not self.default_label or label == self.default_label:
            return False
        return self.is_workday(moment)

    def before_end_of_workday(self, label: str, moment: datetime) -> bool:
        hours = self.for_label(label)
        return hours is not None and hours.before_end_of_workday(moment)
