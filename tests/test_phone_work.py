"""Phone Work filters — lockstep with ios/Kosistenz/PhoneWork.swift."""

from __future__ import annotations

import unittest
from pathlib import Path

import phone_work


ROOT = Path(__file__).resolve().parents[1]


class PhoneWorkTests(unittest.TestCase):
    def test_parse_minutes_from_title(self) -> None:
        self.assertEqual(phone_work.parse_minutes_from_title("45 mins board memo"), 45)
        self.assertEqual(phone_work.parse_minutes_from_title("1h reading"), 60)
        self.assertIsNone(phone_work.parse_minutes_from_title("Call the dentist"))

    def test_filters_match_mac_work_sheet(self) -> None:
        items = [
            {"id": "today", "title": "Today task", "scheduled_date": "2026-09-14", "status": "open"},
            {"id": "parked", "title": "Parked", "scheduled_date": "", "status": "open"},
            {"id": "due", "title": "Due essay", "scheduled_date": "", "due_at": "2026-09-16T23:59:00", "status": "open"},
            {"id": "done", "title": "Finished", "scheduled_date": "2026-09-14", "status": "done"},
        ]
        today = phone_work.filter_items(items, "today", "2026-09-14")
        self.assertEqual([row["id"] for row in today], ["today"])
        parked = phone_work.filter_items(items, "all", "2026-09-14")
        self.assertEqual([row["id"] for row in parked], ["parked", "due"])
        due = phone_work.filter_items(items, "due", "2026-09-14")
        self.assertEqual([row["id"] for row in due], ["due"])
        unplaced = phone_work.filter_items(items, "unplaced", "2026-09-14", unplaced_ids=["parked"])
        self.assertEqual([row["id"] for row in unplaced], ["parked"])

    def test_swift_port_mentions_work_sheet(self) -> None:
        work = (ROOT / "ios" / "Kosistenz" / "PhoneWork.swift").read_text(encoding="utf-8")
        screen = (ROOT / "ios" / "Kosistenz" / "WorkScreen.swift").read_text(encoding="utf-8")
        app = (ROOT / "ios" / "Kosistenz" / "KosistenzApp.swift").read_text(encoding="utf-8")
        calendar = (ROOT / "ios" / "Kosistenz" / "CalendarScreen.swift").read_text(encoding="utf-8")
        project = (ROOT / "ios" / "Kosistenz.xcodeproj" / "project.pbxproj").read_text(encoding="utf-8")
        self.assertIn("enum PhoneWork", work)
        self.assertIn("static func parseMinutesFromTitle", work)
        self.assertIn("static func filterItems", work)
        self.assertIn("struct WorkScreen", screen)
        self.assertIn("Today", screen)
        self.assertIn("Unplaced", screen)
        self.assertIn("case calendar, work", app)
        self.assertNotIn("case today, calendar, todo", app)
        self.assertIn("Fill week", calendar)
        self.assertIn("CalView", calendar)
        self.assertIn("Month", calendar)
        self.assertIn("Year", calendar)
        self.assertIn("WorkScreen.swift in Sources", project)
        self.assertNotIn("TodoScreen.swift", project)


if __name__ == "__main__":
    unittest.main()
