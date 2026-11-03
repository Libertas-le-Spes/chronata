import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from chronata.adapters.storage.reminder_pace_file import ReminderPaceFile
from chronata.use_cases.reminders.reminder_pace import ReminderPace


class StoringTheReminderPace(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "reminders.json"

    def saved(self, content: str) -> ReminderPace:
        self.path.write_text(content)
        return ReminderPaceFile(self.path).load()

    def test_with_nothing_saved_it_is_every_half_hour(self):
        self.assertEqual(ReminderPaceFile(self.path).load(), ReminderPace())

    def test_a_pace_and_off_survive_saving(self):
        store = ReminderPaceFile(self.path)
        for pace in (ReminderPace(timedelta(minutes=45)), ReminderPace(None)):
            with self.subTest(pace=pace):
                store.save(pace)
                self.assertEqual(store.load(), pace)

    def test_a_damaged_file_falls_back_to_every_half_hour(self):
        self.assertEqual(self.saved("{not json"), ReminderPace())

    def test_a_hand_edited_pace_outside_the_allowed_range_falls_back_to_every_half_hour(self):
        for minutes in (1, 0, 241, "30", True, 2.5):
            with self.subTest(minutes=minutes):
                self.assertEqual(self.saved(json.dumps({"clock_out_every_minutes": minutes})), ReminderPace())

    def test_something_other_than_a_setting_falls_back_to_every_half_hour(self):
        for content in ("[30]", '"clock_out_every_minutes"'):
            with self.subTest(content=content):
                self.assertEqual(self.saved(content), ReminderPace())


if __name__ == "__main__":
    unittest.main()
