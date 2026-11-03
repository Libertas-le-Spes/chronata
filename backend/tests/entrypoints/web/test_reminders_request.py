import unittest
from types import SimpleNamespace
from unittest.mock import create_autospec

from chronata.entrypoints.web.requests import changes
from chronata.use_cases.reminders.reminder_setting import ClockOutReminderSetting


def app_with_setting() -> SimpleNamespace:
    return SimpleNamespace(reminder_setting=create_autospec(ClockOutReminderSetting, instance=True))


class TheRemindersRequest(unittest.TestCase):
    def test_a_pace_is_passed_on(self):
        app = app_with_setting()
        changes(app)["/api/reminders"]({"every": 45})
        app.reminder_setting.remind_every.assert_called_once_with(45)

    def test_off_turns_them_off(self):
        app = app_with_setting()
        changes(app)["/api/reminders"]({"off": True})
        app.reminder_setting.turn_off.assert_called_once_with()
        app.reminder_setting.remind_every.assert_not_called()

    def test_off_given_as_anything_but_true_does_not_turn_them_off(self):
        app = app_with_setting()
        changes(app)["/api/reminders"]({"off": "yes", "every": 45})
        app.reminder_setting.turn_off.assert_not_called()


if __name__ == "__main__":
    unittest.main()
