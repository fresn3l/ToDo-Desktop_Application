"""Today's clock — lockstep with ios/Kosistenz/DayTimeline.swift."""

from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path

import phone_today


class IphoneTodayTimelineTests(unittest.TestCase):
    def test_sorts_by_start_and_leaves_unplaced_out(self) -> None:
        events = [
            {
                "id": "chem",
                "title": "CHEM",
                "kind": "hard",
                "status": "",
                "start_at": "2026-09-08T09:30:00",
                "end_at": "2026-09-08T10:20:00",
            }
        ]
        blocks = [
            {
                "id": "essay",
                "title": "Study essay 2",
                "kind": "work",
                "status": "proposed",
                "start_at": "2026-09-08T11:00:00",
                "end_at": "2026-09-08T12:30:00",
            },
            {
                "id": "late",
                "title": "No time yet",
                "kind": "work",
                "status": "",
                "start_at": None,
                "end_at": None,
            },
        ]
        rows = phone_today.timeline_items(events, blocks)
        self.assertEqual([row["id"] for row in rows], ["chem", "essay", "late"])
        self.assertEqual(rows[0]["minutes"], 50)
        self.assertEqual(rows[1]["minutes"], 90)
        self.assertEqual(rows[2]["minutes"], 30)
        self.assertEqual(rows[0]["label"], "Event")
        self.assertEqual(rows[1]["label"], "Work")
        self.assertEqual(
            phone_today.unplaced_titles([{"id": "u1", "title": "Parked thought"}, {"title": ""}]),
            ["Parked thought"],
        )

    def test_now_flag_and_status_label(self) -> None:
        now = datetime(2026, 9, 8, 11, 15, 0)
        rows = phone_today.timeline_items(
            [],
            [
                {
                    "id": "gym",
                    "title": "Legs",
                    "kind": "workout",
                    "status": "locked",
                    "start_at": "2026-09-08T11:00:00",
                    "end_at": "2026-09-08T12:00:00",
                }
            ],
            now=now,
        )
        self.assertEqual(rows[0]["label"], "Gym · locked")
        self.assertTrue(rows[0]["is_now"])

    def test_swift_port_mentions_this_module(self) -> None:
        text = Path(__file__).resolve().parents[1].joinpath("ios", "Kosistenz", "DayTimeline.swift").read_text(
            encoding="utf-8"
        )
        self.assertIn("tests/test_iphone_today_timeline.py", text)
        self.assertIn("phone_today.py", text)
        self.assertIn("struct DayTimelineView", text)
        self.assertIn("label = \"Event\"", text)
        self.assertNotIn("label = \"Class\"", text)
        today = Path(__file__).resolve().parents[1].joinpath("ios", "Kosistenz", "TodayScreen.swift").read_text(
            encoding="utf-8"
        )
        calendar = Path(__file__).resolve().parents[1].joinpath("ios", "Kosistenz", "CalendarScreen.swift").read_text(
            encoding="utf-8"
        )
        self.assertIn("TodayList.entries", today)
        self.assertIn("PackActions.complete", today)
        self.assertIn("DayClockView", calendar)
        self.assertIn("AddEventSheet", calendar)


if __name__ == "__main__":
    unittest.main()
