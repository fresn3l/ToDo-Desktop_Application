"""Today home payload and week-strip miss flags."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import appearance
import insights
import timeline
import work
import workouts


class TodayHomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.root)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.patches = [
            patch.object(work, "_data_dir", lambda: self.root),
            patch.object(workouts, "_data_dir", lambda: self.root),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_appearance_defaults_leave_journal_focus_off(self):
        self.assertFalse(appearance.DEFAULTS["autoFocus"])
        self.assertEqual(appearance.DEFAULTS["todayLayout"], "split")
        self.assertEqual(appearance.DEFAULTS["todayOrder"], "todo,workout,journal")
        self.assertTrue(appearance.DEFAULTS["todayTodo"])

    def test_sanitize_today_dashboard_flags(self):
        cleaned = appearance._sanitize(
            {"todayLayout": "stack", "todayTodo": False, "todayWorkout": "off", "todayJournal": "yes"}
        )
        self.assertEqual(cleaned["todayLayout"], "stack")
        self.assertFalse(cleaned["todayTodo"])
        self.assertFalse(cleaned["todayWorkout"])
        self.assertTrue(cleaned["todayJournal"])

    def test_sanitize_today_order_and_columns(self):
        cleaned = appearance._sanitize(
            {"todayLayout": "columns", "todayOrder": "journal,todo,nope,journal"}
        )
        self.assertEqual(cleaned["todayLayout"], "columns")
        self.assertEqual(cleaned["todayOrder"], "journal,todo,workout")

    def test_today_home_includes_todos_and_expected_kinds(self):
        weekday = str(date.today().weekday())
        workouts.save_week_template(
            {
                "lifts": {weekday: "push"},
                "running": {"enabled": False},
            }
        )
        item = work.create_work_item("Write the paper", scheduled_date=date.today().isoformat())
        work.start_work_item(item["id"])
        home = insights.get_today_home()

        self.assertEqual(home["expected"]["kinds"], ["push"])
        self.assertTrue(home["expected"]["template_label"])
        self.assertEqual(len(home["today"]), 1)
        self.assertEqual(home["today"][0]["status"], "active")
        self.assertIn("workout_day", home)
        self.assertIn("journal_streak", home)

    def test_week_overview_marks_template_misses(self):
        friday = date(2026, 8, 28)
        saturday = date(2026, 8, 29)
        workouts.save_week_template(
            {
                "lifts": {"4": "legs"},
                "running": {"enabled": False},
            }
        )
        with (
            patch.object(workouts, "_today", return_value=saturday),
            patch.object(work, "_today", return_value=saturday),
            patch.object(timeline, "_today", return_value=saturday),
        ):
            overview = timeline.get_week_overview()

        friday_day = next(day for day in overview["days"] if day["date"] == friday.isoformat())
        saturday_day = next(day for day in overview["days"] if day["date"] == saturday.isoformat())
        self.assertEqual(friday_day["expected_kinds"], ["legs"])
        self.assertTrue(friday_day["miss"])
        self.assertEqual(saturday_day["expected_kinds"], [])
        self.assertFalse(saturday_day["miss"])
