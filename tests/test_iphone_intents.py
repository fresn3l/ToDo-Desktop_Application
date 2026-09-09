"""App Intents + widget — lockstep with ios/Kosistenz/AppIntents.swift."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IphoneIntentsTests(unittest.TestCase):
    def test_shortcuts_and_widget_use_the_same_actions(self) -> None:
        intents = (ROOT / "ios" / "Kosistenz" / "AppIntents.swift").read_text(encoding="utf-8")
        actions = (ROOT / "ios" / "Kosistenz" / "PackActions.swift").read_text(encoding="utf-8")
        widget = (ROOT / "ios" / "KosistenzWidget" / "KosistenzWidget.swift").read_text(encoding="utf-8")
        project = (ROOT / "ios" / "Kosistenz.xcodeproj" / "project.pbxproj").read_text(encoding="utf-8")
        self.assertIn("struct ParkWorkIntent", intents)
        self.assertIn("struct ToggleFirstTodoIntent", intents)
        self.assertIn("struct ToggleTodoIntent", intents)
        self.assertIn("struct LogExpectedWorkoutIntent", intents)
        self.assertIn("AppShortcutsProvider", intents)
        self.assertIn("#if !WIDGET_EXTENSION", intents)
        self.assertIn("Park in \\(.applicationName)", intents)
        self.assertIn("static func park(", actions)
        self.assertIn("static func toggleFirstOpen(", actions)
        self.assertIn("static func logExpected(", actions)
        self.assertIn("group.com.kosistenz.app", actions)
        self.assertIn("Button(intent: ToggleTodoIntent", widget)
        self.assertIn("KosistenzTodayWidget", widget)
        self.assertIn("com.kosistenz.app.widget", project)
        self.assertIn("KosistenzWidget.appex", project)
        entitlements = (ROOT / "ios" / "Kosistenz" / "Kosistenz.entitlements").read_text(encoding="utf-8")
        self.assertIn("group.com.kosistenz.app", entitlements)

    def test_today_and_inbox_go_through_pack_actions(self) -> None:
        today = (ROOT / "ios" / "Kosistenz" / "TodayScreen.swift").read_text(encoding="utf-8")
        inbox = (ROOT / "ios" / "Kosistenz" / "InboxScreen.swift").read_text(encoding="utf-8")
        self.assertIn("PackActions.toggle", today)
        self.assertIn("PackActions.addTodo", today)
        self.assertIn("PackActions.logSession", today)
        self.assertIn("PackActions.park", inbox)

    def test_week_and_today_can_add_hard_events(self) -> None:
        week = (ROOT / "ios" / "Kosistenz" / "WeekScreen.swift").read_text(encoding="utf-8")
        today = (ROOT / "ios" / "Kosistenz" / "TodayScreen.swift").read_text(encoding="utf-8")
        actions = (ROOT / "ios" / "Kosistenz" / "PackActions.swift").read_text(encoding="utf-8")
        self.assertIn("AddEventSheet", week)
        self.assertIn("WeekClockView", week)
        self.assertIn("AddEventSheet", today)
        self.assertIn("static func addHardEvent", actions)
        self.assertIn("PhoneCalendar.paint", actions)
        self.assertNotIn("Class", week)


if __name__ == "__main__":
    unittest.main()
