import unittest

from chronata.entrypoints.bar import clock_button as bar
from chronata.use_cases.questions.questions import Answers
from tests.fakes import Fixture, at, hours


class ClickingTheBarAfterBeingAway(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:00:00")
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")
        self.f.app.clocking.clock_in(None, None)
        self.f.at("2026-10-14T18:10:00")
        self.f.app.away.began(600)
        self.f.at("2026-10-14T19:40:00")
        self.f.app.away.ended()

    def click(self, *answers) -> None:
        self.f.desktop.answers = list(answers)
        bar.toggle(self.f.app, self.f.page)

    def shift(self):
        return self.f.app.log.shifts()[0]

    def test_it_asks_about_the_time_away_instead_of_clocking_out(self):
        self.click(None)
        self.assertEqual(self.f.desktop.asked[0][0], "You were away from the PC from 18:00 to 19:40 (1:40), past the end of your shift. Were you working?")
        self.assertIsNone(self.shift().end)

    def test_it_offers_the_four_answers(self):
        self.click(None)
        self.assertEqual(self.f.desktop.asked[0][1], ["Still working", "Clock out now", "Clock out at 18:00, when I left", "Waive 18:00–19:40 and keep working"])

    def test_still_working_keeps_you_clocked_in_and_stops_asking(self):
        self.click("Still working")
        self.assertIsNone(self.shift().end)
        self.assertIsNone(self.f.app.away.to_ask_about())

    def test_clocking_out_now_keeps_the_time_away_with_the_reason(self):
        self.click("Clock out now", "client meeting")
        self.assertEqual((self.shift().end, self.shift().notes), (at("2026-10-14T19:40:00"), ["client meeting"]))
        self.assertIsNone(self.f.app.away.to_ask_about())

    def test_clocking_out_when_you_left_ends_the_shift_then(self):
        self.click("Clock out at 18:00, when I left")
        self.assertEqual(self.shift().end, at("2026-10-14T18:00:00"))

    def test_waiving_keeps_you_clocked_in_without_the_time_away(self):
        self.click("Waive 18:00–19:40 and keep working", "forgot to clock out")
        self.assertIsNone(self.shift().end)
        self.assertEqual(self.shift().worked(self.f.now), at("2026-10-14T18:00:00") - at("2026-10-14T08:00:00"))

    def test_cancelling_changes_nothing_and_asks_again_next_time(self):
        self.click(None)
        self.assertIsNone(self.shift().end)
        self.assertIsNotNone(self.f.app.away.to_ask_about())

    def test_an_empty_reason_changes_nothing(self):
        self.click("Clock out now", "  ")
        self.assertIsNone(self.shift().end)
        self.assertIsNotNone(self.f.app.away.to_ask_about())

    def test_a_refused_change_is_shown_and_asks_again_next_time(self):
        self.f.app.waivers.waive([self.shift().id], "18:30", "18:45", "dinner")
        self.click("Waive 18:00–19:40 and keep working", "forgot to clock out")
        self.assertEqual(self.f.desktop.notices[-1][0], "Could not waive that time")
        self.assertIsNotNone(self.f.app.away.to_ask_about())

    def test_the_click_counts_as_coming_back_when_no_return_was_noted(self):
        self.f.at("2026-10-14T20:00:00")
        self.f.app.away.began(600)
        self.f.at("2026-10-14T21:00:00")
        self.click("Still working")
        self.assertEqual(self.f.desktop.asked[0][0], "You were away from the PC from 19:50 to 21:00 (1:10), past the end of your shift. Were you working?")

    def test_the_click_is_kept_as_the_return_when_the_question_is_cancelled(self):
        self.f.at("2026-10-14T20:00:00")
        self.f.app.away.began(600)
        self.f.at("2026-10-14T21:00:00")
        self.click(None)
        self.f.at("2026-10-14T22:00:00")
        self.assertEqual(self.f.app.away.to_ask_about().stretch.back, at("2026-10-14T21:00:00"))

    def test_without_dialogs_the_click_clocks_out_as_before(self):
        self.f.desktop.dialogs_installed = False
        self.click()
        self.assertIsNotNone(self.shift().end)



class AwayRightAfterClockingIn(unittest.TestCase):
    def test_clocking_out_when_you_left_is_not_offered_because_it_would_end_the_shift_as_it_began(self):
        self.f = Fixture("2026-10-14T18:05:00")
        self.f.app.setup.configure(hours("08:00", "17:00"), "Primary")
        self.f.app.clocking.clock_in(None, None, None, Answers(overtime=True))
        self.f.at("2026-10-14T18:10:00")
        self.f.app.away.began(600)
        self.f.at("2026-10-14T18:40:00")
        self.f.desktop.answers = [None]
        bar.toggle(self.f.app, self.f.page)
        self.assertEqual(self.f.desktop.asked[0][1], ["Still working", "Clock out now", "Waive 18:05–18:40 and keep working"])


if __name__ == "__main__":
    unittest.main()
