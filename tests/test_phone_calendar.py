"""Phone week-clock expand/paint — lockstep with ios/Kosistenz/PhoneCalendar.swift."""

from __future__ import annotations

import unittest
from datetime import datetime
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
        self.assertIn("static func fillWeek", calendar)
        self.assertIn("static func parseICSEvents", calendar)
        self.assertIn("static func assembleWeek", calendar)
        self.assertIn("static func monthWeeks", calendar)
        self.assertIn("static func fillWeek", actions)
        self.assertIn("static func placeWork", actions)
        self.assertIn("static func parkClockItem", actions)
        self.assertIn("static func importICS", actions)
        self.assertIn("phone_blocks", pack)
        self.assertIn("WorkScreen.swift in Sources", project)
        self.assertIn("PlaceWorkSheet.swift in Sources", project)
        self.assertIn("PhoneWork.swift in Sources", project)

    def test_fill_week_packs_unplaced_into_gaps(self) -> None:
        days = phone_calendar.empty_week("2026-09-07", "2026-09-08")
        days[0]["events"] = [
            {
                "id": "office",
                "title": "Office",
                "kind": "hard",
                "status": "locked",
                "start_at": "2026-09-07T09:00:00",
                "end_at": "2026-09-07T10:00:00",
            }
        ]
        items = [
            {
                "id": "essay",
                "title": "Essay",
                "estimate_minutes": 60,
                "status": "open",
            }
        ]
        painted, placed, removed = phone_calendar.fill_week(
            days,
            items,
            "05:30",
            "21:30",
            now=datetime(2026, 9, 7, 9, 0, 0),
        )
        self.assertEqual(removed, [])
        self.assertEqual(len(placed), 1)
        self.assertEqual(placed[0]["kind"], "work")
        self.assertEqual(placed[0]["source"], "iphone")
        self.assertEqual(placed[0]["start_at"], "2026-09-07T10:00:00")
        self.assertEqual(placed[0]["end_at"], "2026-09-07T11:00:00")
        self.assertEqual(painted[0]["blocks"][0]["title"], "Essay")

    def test_fill_week_clears_proposed_then_repacks(self) -> None:
        days = phone_calendar.empty_week("2026-09-07", "2026-09-07")
        days[0]["blocks"] = [
            {
                "id": "old",
                "title": "Old pack",
                "kind": "work",
                "status": "proposed",
                "start_at": "2026-09-07T11:00:00",
                "end_at": "2026-09-07T12:00:00",
                "work_item_id": "essay",
            }
        ]
        painted, placed, removed = phone_calendar.fill_week(
            days,
            [{"id": "essay", "title": "Essay", "estimate_minutes": 50, "status": "open"}],
            "05:30",
            "21:30",
            now=datetime(2026, 9, 7, 5, 0, 0),
        )
        self.assertEqual(removed, ["old"])
        self.assertEqual(len(placed), 1)
        self.assertNotEqual(placed[0]["id"], "old")
        self.assertTrue(all(block["id"] != "old" for block in painted[0]["blocks"]))

    def test_ics_weekly_byday_and_one_off(self) -> None:
        blob = """BEGIN:VCALENDAR
BEGIN:VEVENT
SUMMARY:Office hours
DTSTART:20260908T140000
DTEND:20260908T150000
RRULE:FREQ=WEEKLY;BYDAY=TU,TH
END:VEVENT
BEGIN:VEVENT
SUMMARY:One meeting
DTSTART:20260909T090000
DTEND:20260909T093000
END:VEVENT
END:VCALENDAR
"""
        rows = phone_calendar.parse_ics_events(blob)
        self.assertEqual(rows[0]["title"], "Office hours")
        self.assertEqual(rows[0]["weekdays"], [1, 3])
        self.assertEqual(rows[1]["weekdays"], [])
        self.assertEqual(rows[1]["start_at"], "2026-09-09T09:00:00")

    def test_month_weeks_start_on_monday(self) -> None:
        weeks = phone_calendar.month_weeks(
            2026,
            9,
            "2026-09-14",
            {"2026-09-08": 1},
            {"2026-09-08": 2},
            {"2026-09-14": 1},
        )
        self.assertEqual(weeks[0][0]["date"], "2026-08-31")
        self.assertFalse(weeks[0][0]["in_month"])
        tuesday = weeks[1][1]
        self.assertEqual(tuesday["date"], "2026-09-08")
        self.assertEqual(tuesday["event_count"], 1)
        self.assertTrue(tuesday["has_items"])

    def test_assemble_other_week_paints_hard_events(self) -> None:
        packed = phone_calendar.empty_week("2026-09-07", "2026-09-08")
        packed[1]["events"] = [{"id": "office", "title": "Office", "start_at": "2026-09-08T14:00:00"}]
        event = {
            "id": "office",
            "title": "Office hours",
            "start_at": "2026-09-08T14:00:00",
            "end_at": "2026-09-08T15:00:00",
            "weekdays": [1],
        }
        other = phone_calendar.assemble_week(
            "2026-09-14",
            "2026-09-14",
            packed,
            [event],
            [],
            [],
        )
        self.assertEqual(other[0]["date"], "2026-09-14")
        self.assertEqual(other[1]["events"][0]["title"], "Office hours")
        same = phone_calendar.assemble_week("2026-09-07", "2026-09-08", packed, [event], [], [])
        self.assertEqual(len(same[1]["events"]), 1)

    def test_unplaced_uses_leftover_minutes(self) -> None:
        items = [
            {"id": "a", "title": "Essay", "estimate_minutes": 90, "status": "open"},
            {"id": "b", "title": "Done", "estimate_minutes": 40, "status": "done"},
        ]
        blocks = [
            {
                "work_item_id": "a",
                "start_at": "2026-09-07T10:00:00",
                "end_at": "2026-09-07T11:00:00",
            }
        ]
        rows = phone_calendar.unplaced_from_work(items, blocks)
        self.assertEqual([row["id"] for row in rows], ["a"])
        self.assertEqual(rows[0]["remaining_minutes"], 30)


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
