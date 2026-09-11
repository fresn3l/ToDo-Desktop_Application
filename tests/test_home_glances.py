"""Now/next, dues, free time, and glance actions."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from unittest import mock

import home_glances
import work


class HomeGlanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": self.tmp.name})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_clock_beat_names_now_next_and_gap(self) -> None:
        now = datetime(2026, 9, 9, 10, 0, 0)
        beat = home_glances.clock_beat(
            [
                {
                    "id": "a",
                    "title": "Lecture",
                    "start_at": "2026-09-09T09:00:00",
                    "end_at": "2026-09-09T10:30:00",
                    "kind": "hard",
                    "status": "",
                },
                {
                    "id": "b",
                    "title": "Spanish",
                    "start_at": "2026-09-09T11:00:00",
                    "end_at": "2026-09-09T12:00:00",
                    "kind": "work",
                    "status": "proposed",
                },
            ],
            now=now,
            day_end="21:30",
        )
        self.assertEqual(beat["phase"], "now")
        self.assertEqual(beat["now"]["title"], "Lecture")
        self.assertEqual(beat["next"]["title"], "Spanish")
        self.assertEqual(beat["gap_minutes"], 30)
        self.assertFalse(beat["can_skip"])

    def test_clock_beat_skips_skipped_blocks(self) -> None:
        now = datetime(2026, 9, 9, 10, 0, 0)
        beat = home_glances.clock_beat(
            [
                {
                    "id": "skip-me",
                    "title": "Old block",
                    "start_at": "2026-09-09T09:30:00",
                    "end_at": "2026-09-09T11:00:00",
                    "kind": "work",
                    "status": "skipped",
                },
                {
                    "id": "next",
                    "title": "Lab",
                    "start_at": "2026-09-09T11:00:00",
                    "end_at": "2026-09-09T12:00:00",
                    "kind": "work",
                    "status": "proposed",
                },
            ],
            now=now,
            day_end="21:30",
        )
        self.assertEqual(beat["phase"], "next")
        self.assertIsNone(beat["now"])
        self.assertEqual(beat["next"]["id"], "next")
        self.assertEqual(beat["gap_minutes"], 60)
        self.assertTrue(beat["can_skip"])

    def test_clock_beat_skips_missed_blocks(self) -> None:
        now = datetime(2026, 9, 9, 10, 0, 0)
        beat = home_glances.clock_beat(
            [
                {
                    "id": "miss-me",
                    "title": "Old block",
                    "start_at": "2026-09-09T09:30:00",
                    "end_at": "2026-09-09T11:00:00",
                    "kind": "work",
                    "status": "missed",
                },
                {
                    "id": "next",
                    "title": "Lab",
                    "start_at": "2026-09-09T11:00:00",
                    "end_at": "2026-09-09T12:00:00",
                    "kind": "work",
                    "status": "proposed",
                },
            ],
            now=now,
            day_end="21:30",
        )
        self.assertEqual(beat["phase"], "next")
        self.assertIsNone(beat["now"])
        self.assertEqual(beat["next"]["id"], "next")

    def test_dues_this_week_are_deadlines_not_busy(self) -> None:
        from datetime import date, timedelta

        today = date.today()
        friday = today - timedelta(days=today.weekday()) + timedelta(days=4)
        work.create_work_item(
            "Essay 2",
            scheduled_date=None,
            due_at=f"{friday.isoformat()}T23:59:00",
            estimate_minutes=60,
        )
        packed = home_glances.dues_this_week(today)
        titles = [row["title"] for row in packed["items"]]
        self.assertIn("Essay 2", titles)
        self.assertEqual(packed["items"][0]["due"], friday.isoformat())

    def test_do_today_sets_the_day_not_a_clock(self) -> None:
        item = work.create_work_item("Parked spanish", scheduled_date=None, estimate_minutes=45)
        packed = home_glances.glance_do_today(item["id"])
        self.assertEqual(packed["scheduled_date"], work._today().isoformat())
        self.assertIsNone(packed.get("start_at"))

    def test_plus15_adds_estimate_minutes(self) -> None:
        item = work.create_work_item("Lab writeup", scheduled_date=work._today().isoformat(), estimate_minutes=30)
        packed = home_glances.glance_plus15(item["id"])
        self.assertEqual(packed["estimate_minutes"], 45)

    def test_park_clears_the_day(self) -> None:
        item = work.create_work_item("Gym film", scheduled_date=work._today().isoformat())
        packed = home_glances.glance_park_work(item["id"])
        self.assertIsNone(packed["scheduled_date"])

    def test_free_today_compares_capacity_to_open_estimates(self) -> None:
        work.create_work_item(
            "Two hour paper",
            scheduled_date=work._today().isoformat(),
            estimate_minutes=120,
        )
        glance = home_glances.free_today_glance()
        self.assertGreaterEqual(glance["needed_minutes"], 120)
        self.assertIn("free_minutes", glance)
        self.assertGreaterEqual(glance["open_count"], 1)


if __name__ == "__main__":
    unittest.main()
