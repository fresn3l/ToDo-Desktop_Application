"""Phone week-clock expand/paint — lockstep with ios/Kosistenz/PhoneCalendar.swift."""

from __future__ import annotations

import unittest
from pathlib import Path

import phone_calendar


ROOT = Path(__file__).resolve().parents[1]


class PhoneCalendarTests(unittest.TestCase):
    def test_parse_hhmm_matches_mac_awake_fields(self) -> None:
        self.assertEqual(phone_calendar.parse_hhmm("0530"), (5, 30))
        self.assertEqual(phone_calendar.parse_hhmm("21:30"), (21, 30))
        self.assertEqual(phone_calendar.clock_window("0530", "2130"), (5 * 60 + 30, 21 * 60 + 30))

    def test_weekly_chips_paint_selected_days(self) -> None:
        event = {
            "id": "office",
            "title": "Office hours",
            "start_at": "2026-09-07T14:00:00",
            "end_at": "2026-09-07T15:00:00",
            "weekdays": [0, 2],
        }
        rows = phone_calendar.expand_hard_event(event, "2026-09-07", "2026-09-13")
        self.assertEqual([row["occurrence_date"] for row in rows], ["2026-09-07", "2026-09-09"])
        self.assertEqual(rows[0]["kind"], "hard")
        self.assertEqual(phone_calendar.kind_label("hard", "locked"), "Event · locked")

    def test_one_shot_overnight_spans_both_days(self) -> None:
        event = {
            "id": "lab",
            "title": "Night lab",
            "start_at": "2026-09-08T22:00:00",
            "end_at": "2026-09-09T01:00:00",
            "weekdays": [],
        }
        rows = phone_calendar.expand_hard_event(event, "2026-09-07", "2026-09-13")
        self.assertEqual([row["occurrence_date"] for row in rows], ["2026-09-08", "2026-09-09"])
        self.assertEqual(rows[0]["start_at"], "2026-09-08T22:00:00")
        self.assertEqual(rows[0]["end_at"], "2026-09-09T00:00:00")
        self.assertEqual(rows[1]["start_at"], "2026-09-09T00:00:00")
        self.assertEqual(rows[1]["end_at"], "2026-09-09T01:00:00")

    def test_paint_injects_events_without_writing_blocks(self) -> None:
        days = [
            {"date": "2026-09-08", "events": [], "blocks": [{"id": "study", "title": "Essay"}]},
            {"date": "2026-09-09", "events": [], "blocks": []},
        ]
        event = {
            "id": "office",
            "title": "Office hours",
            "start_at": "2026-09-08T14:00:00",
            "end_at": "2026-09-08T15:00:00",
            "weekdays": [1],
        }
        painted = phone_calendar.paint_event_on_days(days, event, "2026-09-07", "2026-09-13")
        self.assertEqual(painted[0]["events"][0]["title"], "Office hours")
        self.assertEqual(painted[0]["blocks"][0]["id"], "study")
        self.assertEqual(painted[1]["events"], [])

    def test_swift_port_mentions_add_event(self) -> None:
        calendar = (ROOT / "ios" / "Kosistenz" / "PhoneCalendar.swift").read_text(encoding="utf-8")
        actions = (ROOT / "ios" / "Kosistenz" / "PackActions.swift").read_text(encoding="utf-8")
        sheet = (ROOT / "ios" / "Kosistenz" / "AddEventSheet.swift").read_text(encoding="utf-8")
        clock = (ROOT / "ios" / "Kosistenz" / "DayClock.swift").read_text(encoding="utf-8")
        pack = (ROOT / "ios" / "Kosistenz" / "SyncPack.swift").read_text(encoding="utf-8")
        project = (ROOT / "ios" / "Kosistenz.xcodeproj" / "project.pbxproj").read_text(encoding="utf-8")
        self.assertIn("enum PhoneCalendar", calendar)
        self.assertIn("static func expandHardEvent", calendar)
        self.assertIn("static func paint(", calendar)
        self.assertIn("label = \"Event\"", calendar)
        self.assertIn("static func addHardEvent", actions)
        self.assertIn("source: \"iphone\"", actions)
        self.assertIn("hard_events", actions)
        self.assertIn("struct AddEventSheet", sheet)
        self.assertIn("Repeats weekly", sheet)
        self.assertIn("struct DayClockView", clock)
        self.assertIn("struct WeekClockView", clock)
        self.assertIn("hard_events", pack)
        self.assertIn("day_start", pack)
        self.assertIn("dues", pack)
        self.assertIn("PhoneCalendar.swift in Sources", project)
        self.assertIn("AddEventSheet.swift in Sources", project)
        self.assertIn("DayClock.swift in Sources", project)
        self.assertNotIn("label = \"Class\"", calendar)


if __name__ == "__main__":
    unittest.main()
