import io
import unittest
from contextlib import redirect_stdout
from datetime import time

from chronata.entrypoints.cli.hours_prompt import ask_hours
from chronata.timekeeping.hours.working_day import Lunch, WorkingDay


class Typing(unittest.TestCase):
    def answers(self, *typed: str, current: WorkingDay | None = None) -> tuple[tuple[str, str], list[str], str]:
        queue, asked, said = list(typed), [], io.StringIO()

        def ask(prompt: str) -> str:
            asked.append(prompt)
            return queue.pop(0)

        with redirect_stdout(said):
            result = ask_hours(ask, current)
        self.assertEqual(queue, [], "every answer was used")
        return result, asked, said.getvalue()

    def test_start_end_lunch_start_and_minutes_as_numbers(self):
        result, asked, _ = self.answers("830", "1730", "1200", "45")
        self.assertEqual(result, ("08:30 to 17:30", "12:00 for 45 min"))
        self.assertEqual(asked, ["Shift starts at (e.g. 830): ", "Shift ends at (e.g. 1730): ",
                                 "Lunch starts at (e.g. 1200, Enter for no lunch): ", "Lunch in minutes (e.g. 45, Enter for no lunch): "])

    def test_enter_at_lunch_start_means_no_lunch(self):
        result, asked, _ = self.answers("8", "17", "")
        self.assertEqual((result, len(asked)), (("08:00 to 17:00", ""), 3))

    def test_enter_at_lunch_minutes_also_means_no_lunch(self):
        self.assertEqual(self.answers("8", "17", "12", "")[0], ("08:00 to 17:00", ""))

    def test_a_wrong_answer_is_explained_and_asked_again(self):
        result, asked, said = self.answers("8:30", "830", "1730", "1200", "45 min", "45")
        self.assertEqual(result, ("08:30 to 17:30", "12:00 for 45 min"))
        self.assertIn("type numbers only, like 830 or 1730", said)
        self.assertEqual(len(asked), 6)

    def test_enter_keeps_the_current_shift_times(self):
        current = WorkingDay(time(8, 30), time(17, 30), Lunch(time(12), 60))
        result, asked, _ = self.answers("", "", "1300", "30", current=current)
        self.assertEqual(result, ("08:30 to 17:30", "13:00 for 30 min"))
        self.assertEqual(asked[:2], ["Shift starts at [0830]: ", "Shift ends at [1730]: "])

    def test_with_no_current_times_enter_is_asked_again(self):
        _, asked, said = self.answers("", "9", "17", "")
        self.assertEqual(len(asked), 4)
        self.assertIn("type numbers only", said)
