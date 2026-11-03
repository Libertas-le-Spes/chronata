import unittest
from datetime import timedelta
from unittest.mock import create_autospec

from chronata.presenters.page.facts import PageFacts
from chronata.presenters.page.reminders import state
from chronata.use_cases.reminders.reminder_pace import ReminderPace


def shown(pace: ReminderPace) -> dict:
    facts = create_autospec(PageFacts, instance=True)
    facts.reminder_pace = pace
    return state(facts)["reminders"]


class RemindersOnThePage(unittest.TestCase):
    def test_the_pace_is_shown_in_minutes(self):
        self.assertEqual(shown(ReminderPace(timedelta(minutes=45))), {"clockOutEvery": 45})

    def test_off_is_shown_as_no_pace(self):
        self.assertEqual(shown(ReminderPace(None)), {"clockOutEvery": None})


if __name__ == "__main__":
    unittest.main()
