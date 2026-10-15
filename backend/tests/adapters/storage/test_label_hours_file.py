import json
import tempfile
import unittest
from datetime import time
from pathlib import Path

from chronata.adapters.storage.label_hours_file import LabelHoursFile
from chronata.timekeeping.hours.working_day import WorkingDay

ONE_SET_OF_HOURS = {"shift": {"start": "08:30", "end": "17:30"}, "lunch": {"start": "12:00", "minutes": 60},
                    "workdays": ["mon", "tue", "wed", "thu", "fri"], "default_label": "Northwind"}


class StoringHoursPerLabel(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "rules.json"

    def test_the_single_set_of_hours_from_before_becomes_the_default_labels(self):
        self.path.write_text(json.dumps(ONE_SET_OF_HOURS))
        hours = LabelHoursFile(self.path).load()
        self.assertEqual((hours.default_label, hours.labels(), hours.main.daily_hours), ("Northwind", ["Northwind"], 8))

    def test_hours_and_no_set_hours_survive_saving(self):
        store = LabelHoursFile(self.path)
        store.save_hours("Globex", WorkingDay(time(9), time(15)))
        store.save_hours("Freelance", None)
        hours = LabelHoursFile(self.path).load()
        self.assertEqual((hours.for_label("Globex").daily_hours, hours.for_label("Freelance"), hours.labels()), (6, None, ["Globex", "Freelance"]))

    def test_a_rename_carries_the_hours(self):
        store = LabelHoursFile(self.path)
        store.save_hours("Globex", WorkingDay(time(9), time(15)))
        store.rename("Globex", "Globex Ltd")
        self.assertEqual(LabelHoursFile(self.path).load().labels(), ["Globex Ltd"])


if __name__ == "__main__":
    unittest.main()
