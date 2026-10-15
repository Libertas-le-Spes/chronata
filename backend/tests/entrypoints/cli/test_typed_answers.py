import io
import unittest
from contextlib import redirect_stdout
from datetime import time

from chronata.entrypoints.cli.typed_answers import ask_choice, ask_inputs
from chronata.timekeeping.hours.working_day import Lunch, WorkingDay
from chronata.use_cases.questions.questions import HOURS_INPUTS, LabelNeedsHours, filled_in, hours_values


class Typing(unittest.TestCase):
    def typed(self, run, *answers: str):
        queue, asked, said = list(answers), [], io.StringIO()

        def ask(prompt: str) -> str:
            asked.append(prompt)
            return queue.pop(0)

        with redirect_stdout(said):
            result = run(ask)
        self.assertEqual(queue, [], "every answer was used")
        return result, asked, said.getvalue()

    def setup_answers(self, *answers: str, current: WorkingDay | None = None):
        inputs = filled_in(HOURS_INPUTS, hours_values(current))
        return self.typed(lambda ask: ask_inputs(ask, inputs), *answers)

    def test_the_four_setup_questions_take_numbers(self):
        result, asked, _ = self.setup_answers("830", "1730", "1200", "45")
        self.assertEqual(result, {"shift_start": "08:30", "shift_end": "17:30", "lunch_start": "12:00", "lunch_minutes": "45"})
        self.assertEqual(asked, ["Shift starts at [e.g. 830]: ", "Shift ends at [e.g. 1730]: ",
                                 "Lunch starts at (leave empty for no lunch) [e.g. 1200]: ", "Lunch in minutes (leave empty for no lunch) [e.g. 45]: "])

    def test_enter_at_lunch_start_means_no_lunch_and_ends_the_questions(self):
        result, asked, _ = self.setup_answers("8", "17", "")
        self.assertEqual((result, len(asked)), ({"shift_start": "08:00", "shift_end": "17:00"}, 3))

    def test_a_wrong_answer_is_explained_and_asked_again(self):
        result, asked, said = self.setup_answers("8:30", "830", "1730", "1200", "45 min", "45")
        self.assertEqual(result["lunch_minutes"], "45")
        self.assertIn("type numbers only, like 830 or 1730", said)
        self.assertEqual(len(asked), 6)

    def test_enter_keeps_the_shift_times_shown_but_still_opts_out_of_lunch(self):
        current = WorkingDay(time(8, 30), time(17, 30), Lunch(time(12), 60))
        result, asked, _ = self.setup_answers("", "", "", current=current)
        self.assertEqual(result, {"shift_start": "08:30", "shift_end": "17:30"})
        self.assertEqual(asked, ["Shift starts at [0830]: ", "Shift ends at [1730]: ", "Lunch starts at (leave empty for no lunch) [now 1200]: "])

    def test_a_new_label_asks_its_choice_then_the_same_four_setup_questions(self):
        (label, given), asked, said = self.typed(lambda ask: ask_choice(ask, LabelNeedsHours("Globex")), "3", "1", "9", "1500", "")
        self.assertEqual((label, given), (None, {"new_label": True, "shift_start": "09:00", "shift_end": "15:00"}))
        self.assertIn("  1) Save its hours\n  2) No set hours", said)
        self.assertIn("type a number from 1 to 2", said)

    def test_enter_at_the_choice_cancels(self):
        self.assertIsNone(self.typed(lambda ask: ask_choice(ask, LabelNeedsHours("Globex")), "")[0])
