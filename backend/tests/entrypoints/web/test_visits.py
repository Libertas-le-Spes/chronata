import unittest

from chronata.entrypoints.web.visits import LAUNCH_CODE_SECONDS, VISIT_SECONDS, Visits


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Visiting(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.visits = Visits(self.clock)

    def test_a_launch_code_opens_one_visit(self):
        code = self.visits.launch_code()
        visit = self.visits.enter(code)
        self.assertEqual(self.visits.find(visit.id), visit)

    def test_a_launch_code_works_only_once(self):
        code = self.visits.launch_code()
        self.visits.enter(code)
        self.assertIsNone(self.visits.enter(code))

    def test_a_launch_code_stops_working_after_a_minute(self):
        code = self.visits.launch_code()
        self.clock.now += LAUNCH_CODE_SECONDS
        self.assertIsNone(self.visits.enter(code))

    def test_a_made_up_code_opens_nothing(self):
        self.visits.launch_code()
        self.assertIsNone(self.visits.enter("made-up"))
        self.assertIsNone(self.visits.enter(""))

    def test_a_visit_ends_after_twelve_hours(self):
        visit = self.visits.enter(self.visits.launch_code())
        self.clock.now += VISIT_SECONDS
        self.assertIsNone(self.visits.find(visit.id))

    def test_each_visit_has_its_own_form_token(self):
        first = self.visits.enter(self.visits.launch_code())
        second = self.visits.enter(self.visits.launch_code())
        self.assertNotEqual(first.form_token, second.form_token)
        self.assertNotEqual(first.id, first.form_token)


if __name__ == "__main__":
    unittest.main()
