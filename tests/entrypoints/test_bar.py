import unittest

from chronata.entrypoints.omarchy import bar
from chronata.timekeeping.pc_sessions import Boot
from tests.fakes import Fixture, at


class ClickingTheBarWhenClockedOut(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:05:00")
        self.f.sheet.configure("12:00 for 60 min", "08:00 to 17:00", "Northwind")
        self.desktop = self.f.desktop

    def click(self, *answers) -> None:
        self.desktop.answers = list(answers)
        bar.toggle(self.f.app)

    def labels(self) -> list[str]:
        return [shift.label for shift in self.f.sheet.shifts()]

    def test_it_suggests_the_default_and_enter_clocks_in_on_it(self):
        self.click("Northwind")
        self.assertEqual(self.desktop.asked[0][1], "Northwind")
        self.assertEqual(self.labels(), ["Northwind"])

    def test_closing_the_question_clocks_nothing(self):
        self.click(None)
        self.assertEqual(self.labels(), [])

    def test_another_label_on_a_workday_is_confirmed_first(self):
        self.click("Acme", "Clock in on Acme")
        self.assertIn("Northwind is your default", self.desktop.asked[1][0])
        self.assertEqual(self.labels(), ["Acme"])

    def test_the_confirmation_can_switch_back_to_the_default(self):
        self.click("Acme", "Use Northwind")
        self.assertEqual(self.labels(), ["Northwind"])

    def test_cancelling_the_confirmation_leaves_you_clocked_out(self):
        self.click("Acme", None)
        self.assertEqual(self.labels(), [])
        self.assertEqual(bar.status(self.f.sheet)["state"], "out")

    def test_a_typo_is_matched_to_the_existing_label(self):
        self.click("Northwind")
        self.f.at("2026-10-14T10:00:00")
        self.f.sheet.clock_out(None, None)
        self.f.at("2026-10-15T08:00:00")
        self.click("Northwnid", "Northwind")
        self.assertEqual(self.labels(), ["Northwind", "Northwind"])

    def test_the_tooltip_names_the_label_you_are_working_on(self):
        self.click("Northwind")
        self.assertTrue(bar.status(self.f.sheet)["tooltip"].startswith("Working on Northwind since 08:05"))



class StartingFromWhenThePcCameOn(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:05:00")
        self.f.sheet.configure("12:00 for 60 min", "08:00 to 17:00", "Northwind")

    def pc_on(self, since: str) -> None:
        self.f.power.boot_list = [Boot("today", at(since), self.f.now, True)]

    def click(self, *answers) -> None:
        self.f.desktop.answers = list(answers)
        bar.toggle(self.f.app)

    def test_the_question_shows_how_long_the_pc_has_been_on(self):
        self.pc_on("2026-10-14T07:50:00")
        self.click(None)
        self.assertIn("The PC has been on since 07:50 (0:15)", self.f.desktop.asked[0][0])

    def test_you_can_start_from_when_the_pc_came_on(self):
        self.pc_on("2026-10-14T07:50:00")
        self.click("Northwind", "Since 07:50")
        shift = self.f.sheet.shifts()[0]
        self.assertEqual((shift.start, shift.notes), (at("2026-10-14T07:50:00"), ["started when the PC came on"]))

    def test_or_from_now(self):
        self.pc_on("2026-10-14T07:50:00")
        self.click("Northwind", "From now")
        self.assertEqual(self.f.sheet.shifts()[0].start, at("2026-10-14T08:05:00"))

    def test_another_label_gets_both_questions(self):
        self.pc_on("2026-10-14T07:50:00")
        self.click("Acme", "Since 07:50", "Clock in on Acme")
        shift = self.f.sheet.shifts()[0]
        self.assertEqual((shift.label, shift.start), ("Acme", at("2026-10-14T07:50:00")))

    def test_a_pc_on_for_only_a_few_minutes_is_not_asked_about(self):
        self.pc_on("2026-10-14T08:02:00")
        self.click("Northwind")
        self.assertEqual(self.f.sheet.shifts()[0].start, at("2026-10-14T08:05:00"))

    def test_time_already_clocked_since_the_pc_came_on_is_not_offered_again(self):
        self.pc_on("2026-10-14T07:50:00")
        self.click("Northwind", "From now")
        self.f.at("2026-10-14T10:00:00")
        self.f.sheet.clock_out(None, None)
        self.f.at("2026-10-14T11:00:00")
        self.click("Acme", "Clock in on Acme")
        self.assertEqual(self.f.sheet.shifts()[-1].start, at("2026-10-14T11:00:00"))


if __name__ == "__main__":
    unittest.main()
