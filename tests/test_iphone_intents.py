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
        self.assertIn("static func complete(", actions)
        self.assertIn("static func assignToToday(", actions)
        self.assertIn("group.com.kosistenz.app", actions)
        self.assertIn("Button(intent: ToggleTodoIntent", widget)
        self.assertIn("KosistenzTodayWidget", widget)
        self.assertIn("com.kosistenz.app.widget", project)
        self.assertIn("KosistenzWidget.appex", project)
        self.assertIn("TodayList.swift", project)
        self.assertIn("EventAlerts.swift", project)
        entitlements = (ROOT / "ios" / "Kosistenz" / "Kosistenz.entitlements").read_text(encoding="utf-8")
        self.assertIn("group.com.kosistenz.app", entitlements)

    def test_three_tabs_and_pack_actions(self) -> None:
        today = (ROOT / "ios" / "Kosistenz" / "TodayScreen.swift").read_text(encoding="utf-8")
        todo = (ROOT / "ios" / "Kosistenz" / "TodoScreen.swift").read_text(encoding="utf-8")
        calendar = (ROOT / "ios" / "Kosistenz" / "CalendarScreen.swift").read_text(encoding="utf-8")
        app = (ROOT / "ios" / "Kosistenz" / "KosistenzApp.swift").read_text(encoding="utf-8")
        alerts = (ROOT / "ios" / "Kosistenz" / "EventAlerts.swift").read_text(encoding="utf-8")
        listing = (ROOT / "ios" / "Kosistenz" / "TodayList.swift").read_text(encoding="utf-8")
        self.assertIn("PackActions.complete", today)
        self.assertIn("PackActions.addTodo", today)
        self.assertIn("TodayCheckRow", today)
        self.assertIn("PackActions.park", todo)
        self.assertIn("PackActions.assignToToday", todo)
        self.assertIn("AddEventSheet", calendar)
        self.assertIn("WeekClockView", calendar)
        self.assertIn("DayClockView", calendar)
        self.assertIn("case today, calendar, todo", app)
        self.assertNotIn("JournalScreen", app)
        self.assertNotIn("InboxScreen", app)
        self.assertIn("static let offsets = [30, 15, 5]", alerts)
        self.assertIn("kosistenz.event.", alerts)
        self.assertIn("func upcomingClockItems", listing)
        plist = (ROOT / "ios" / "Kosistenz" / "Info.plist").read_text(encoding="utf-8")
        self.assertIn("NSUserNotificationsUsageDescription", plist)


if __name__ == "__main__":
    unittest.main()
