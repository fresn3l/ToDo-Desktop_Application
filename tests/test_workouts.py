"""Tests for the workout log."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import workouts


class WorkoutStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.patcher = mock.patch.object(workouts, "_data_dir", lambda: Path(self._tmp.name))
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()
        self._tmp.cleanup()

    def test_running_session_stores_miles(self) -> None:
        day = workouts.add_workout_session("2026-08-28", "running", miles=3.2, minutes=28)
        self.assertTrue(day["done"])
        self.assertEqual(day["miles"], 3.2)
        self.assertEqual(day["sessions"][0]["kind"], "running")

    def test_other_requires_label(self) -> None:
        with self.assertRaises(ValueError):
            workouts.add_workout_session("2026-08-28", "other")
        day = workouts.add_workout_session("2026-08-28", "other", other_label="Pickleball", minutes=45)
        self.assertEqual(day["sessions"][0]["label"], "Pickleball")

    def test_weight_and_multiple_sessions(self) -> None:
        workouts.save_body_weight("2026-08-28", 182.4)
        workouts.add_workout_session("2026-08-28", "push")
        day = workouts.add_workout_session("2026-08-28", "running", miles=1)
        self.assertEqual(day["body_weight"], 182.4)
        self.assertEqual(day["session_count"], 2)
        metrics = workouts.workout_metrics(7)
        self.assertEqual(metrics["by_kind_raw"]["push"], 1)
        self.assertEqual(metrics["by_kind_raw"]["running"], 1)
        self.assertEqual(metrics["miles"], 1)
        days = workouts.list_all_workout_days()
        self.assertGreaterEqual(len(days), 1)

    def test_week_template_miss_stays_on_that_date(self) -> None:
        friday = date(2026, 8, 28)
        saturday = date(2026, 8, 29)
        workouts.save_week_template(
            {
                "lifts": {"4": "legs"},
                "running": {"enabled": False},
            }
        )
        with mock.patch.object(workouts, "_today", return_value=saturday):
            stats = workouts.workout_plan_analytics(7)
        miss_dates = [row["date"] for row in stats["misses"]]
        self.assertIn(friday.isoformat(), miss_dates)
        self.assertNotIn(saturday.isoformat(), miss_dates)
        self.assertEqual(stats["missed"], 1)
        self.assertEqual(stats["misses"][0]["kind"], "legs")

        workouts.add_workout_session(friday.isoformat(), "legs")
        with mock.patch.object(workouts, "_today", return_value=saturday):
            stats = workouts.workout_plan_analytics(7)
        self.assertEqual(stats["missed"], 0)
        self.assertEqual(stats["done"], 1)

    def test_today_is_not_a_template_miss(self) -> None:
        friday = date(2026, 8, 28)
        workouts.save_week_template(
            {
                "lifts": {"4": "legs"},
                "running": {"enabled": False},
            }
        )
        with mock.patch.object(workouts, "_today", return_value=friday):
            stats = workouts.workout_plan_analytics(7)
        miss_dates = [row["date"] for row in stats["misses"]]
        self.assertNotIn(friday.isoformat(), miss_dates)

    def test_expected_kinds_default_monday_push(self) -> None:
        monday = date(2026, 8, 24)
        kinds = workouts.expected_kinds_for_date(monday, workouts.DEFAULT_WEEK_TEMPLATE)
        self.assertIn("push", kinds)

    def test_lift_day_needs_no_miles(self) -> None:
        day = workouts.add_workout_session("2026-08-28", "legs")
        self.assertEqual(day["sessions"][0]["kind"], "legs")
        self.assertIsNone(day["sessions"][0]["miles"])


if __name__ == "__main__":
    unittest.main()
