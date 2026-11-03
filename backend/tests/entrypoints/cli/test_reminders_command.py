import unittest
from unittest.mock import create_autospec

from chronata.entrypoints.cli.main import parser
from chronata.use_cases.reminders.reminder_setting import ClockOutReminderSetting
from chronata.wiring import App


def run(typed: list[str]) -> App:
    app = create_autospec(App, instance=True)
    app.reminder_setting = create_autospec(ClockOutReminderSetting, instance=True)
    args = parser().parse_args(typed)
    args.run(args, app)
    return app


class TheRemindersCommand(unittest.TestCase):
    def test_every_passes_the_minutes_on(self):
        run(["reminders", "--every", "45"]).reminder_setting.remind_every.assert_called_once_with(45)

    def test_off_turns_them_off(self):
        run(["reminders", "--off"]).reminder_setting.turn_off.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
