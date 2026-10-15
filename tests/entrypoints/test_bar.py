import unittest

from chronata.entrypoints import clock_button as bar
from chronata.timekeeping.pc_sessions import Boot
from tests.fakes import Fixture, at


class ClickingTheBarWhenClockedOut(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:05:00")
        self.f.app.setup.configure("12:00 for 60 min", "08:00 to 17:00", "Northwind")
        self.f.app.labels.create("Acme", "", "", no_set_hours=True)
        self.desktop = self.f.desktop

    def click(self, *answers) -> None:
        self.desktop.answers = list(answers)
        bar.toggle(self.f.app)

    def labels(self) -> list[str]:
        return [shift.label for shift in self.f.app.log.shifts()]

    def test_it_suggests_the_default_and_enter_clocks_in_on_it(self):
        self.click("Northwind")
        self.assertEqual(self.desktop.asked[0][1], "Northwind")
        self.assertEqual(self.labels(), ["Northwind"])

    def test_with_no_way_to_ask_it_opens_the_page_at_the_label_box(self):
        self.desktop.dialogs_installed = False
        self.click()
        self.assertTrue(self.desktop.opened[0].endswith("#clock-in"))
        self.assertEqual(self.labels(), [])

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
        self.assertEqual(bar.status(self.f.app)["state"], "out")

    def test_a_typo_is_matched_to_the_existing_label(self):
        self.click("Northwind")
        self.f.at("2026-10-14T10:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-15T08:00:00")
        self.click("Northwnid", "Northwind")
        self.assertEqual(self.labels(), ["Northwind", "Northwind"])

    def test_the_tooltip_names_the_label_you_are_working_on(self):
        self.click("Northwind")
        self.assertTrue(bar.status(self.f.app)["tooltip"].startswith("Working on Northwind, 0:00 today since 08:05"))



class StartingFromWhenThePcCameOn(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:05:00")
        self.f.app.setup.configure("12:00 for 60 min", "08:00 to 17:00", "Northwind")
        self.f.app.labels.create("Acme", "", "", no_set_hours=True)

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
        shift = self.f.app.log.shifts()[0]
        self.assertEqual((shift.start, shift.notes), (at("2026-10-14T07:50:00"), ["started when the PC came on"]))

    def test_a_shift_from_when_the_pc_came_on_carries_that_proof_in_its_explanation(self):
        self.pc_on("2026-10-14T07:50:00")
        self.f.app.pc.record_sessions()
        self.click("Northwind", "Since 07:50")
        day = (self.f.data / "Northwind" / "Days" / "2026-10-14.md").read_text()
        self.assertIn("| 07:50:00 | – |", day)
        self.assertIn("  - started when the PC came on at 07:50:00 · not yet independently timestamped", day)

    def test_the_bar_counts_the_whole_day_from_when_the_pc_came_on(self):
        self.pc_on("2026-10-14T07:50:00")
        self.click("Northwind", "Since 07:50")
        self.f.at("2026-10-14T09:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T09:30:00")
        self.f.app.clocking.clock_in(None, None, "Northwind")
        self.f.at("2026-10-14T10:00:00")
        shown = bar.status(self.f.app)
        self.assertEqual(shown["elapsed"], "1:40")
        self.assertIn("1:40 today since 07:50:00", shown["tooltip"])

    def test_the_bar_counts_only_the_label_you_are_on(self):
        self.pc_on("2026-10-14T07:50:00")
        self.click("Northwind", "Since 07:50")
        self.f.at("2026-10-14T12:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T18:00:00")
        self.f.app.clocking.clock_in(None, None, "Acme", off_default=True)
        self.f.at("2026-10-14T18:30:00")
        self.assertIn("0:30 today since 18:00:00", bar.status(self.f.app)["tooltip"])

    def test_or_from_now(self):
        self.pc_on("2026-10-14T07:50:00")
        self.click("Northwind", "From now")
        self.assertEqual(self.f.app.log.shifts()[0].start, at("2026-10-14T08:05:00"))

    def test_another_label_gets_both_questions(self):
        self.pc_on("2026-10-14T07:50:00")
        self.click("Acme", "Since 07:50", "Clock in on Acme")
        shift = self.f.app.log.shifts()[0]
        self.assertEqual((shift.label, shift.start), ("Acme", at("2026-10-14T07:50:00")))

    def test_a_pc_on_for_only_a_few_minutes_is_not_asked_about(self):
        self.pc_on("2026-10-14T08:02:00")
        self.click("Northwind")
        self.assertEqual(self.f.app.log.shifts()[0].start, at("2026-10-14T08:05:00"))

    def test_time_already_clocked_since_the_pc_came_on_is_not_offered_again(self):
        self.pc_on("2026-10-14T07:50:00")
        self.click("Northwind", "From now")
        self.f.at("2026-10-14T10:00:00")
        self.f.app.clocking.clock_out(None, None)
        self.f.at("2026-10-14T11:00:00")
        self.click("Acme", "Clock in on Acme")
        self.assertEqual(self.f.app.log.shifts()[-1].start, at("2026-10-14T11:00:00"))


class ANewLabelFromTheBar(unittest.TestCase):
    def setUp(self):
        self.f = Fixture("2026-10-14T08:05:00")
        self.f.app.setup.configure("12:00 for 60 min", "08:00 to 17:00", "Northwind")

    def test_typing_a_new_label_asks_its_hours_then_clocks_in(self):
        self.f.desktop.answers = ["Globex", "09:00 to 15:00", "", "Clock in on Globex"]
        bar.toggle(self.f.app)
        self.assertEqual(self.f.app.log.shifts()[0].label, "Globex")
        self.assertEqual(self.f.app.log.hours.for_label("Globex").daily_hours, 6)

    def test_cancelling_the_hours_question_clocks_nothing(self):
        self.f.desktop.answers = ["Globex", None]
        bar.toggle(self.f.app)
        self.assertEqual((self.f.app.log.shifts(), self.f.app.log.hours.labels()), ([], ["Northwind"]))


if __name__ == "__main__":
    unittest.main()
