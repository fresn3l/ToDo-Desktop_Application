"""Tests for the workout log."""

from __future__ import annotations

import tempfile
import unittest
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

    def test_lift_day_needs_no_miles(self) -> None:
        day = workouts.add_workout_session("2026-08-28", "legs")
        self.assertEqual(day["sessions"][0]["kind"], "legs")
        self.assertIsNone(day["sessions"][0]["miles"])


if __name__ == "__main__":
    unittest.main()
