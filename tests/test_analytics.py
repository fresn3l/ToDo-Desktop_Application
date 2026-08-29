"""Tests for the Analytics payload."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import insights
import work
import workouts


class AnalyticsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        path = Path(self._tmp.name)
        self.patches = [
            mock.patch.object(work, "_data_dir", lambda: path),
            mock.patch.object(workouts, "_data_dir", lambda: path),
            mock.patch.object(insights, "_journal_entries_in_range", return_value=[]),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in self.patches:
            patcher.stop()
        self._tmp.cleanup()

    def test_analytics_includes_journal_workout_and_work(self) -> None:
        data = insights.get_analytics(30)
        self.assertEqual(data["days"], 30)
        self.assertIn("entries", data["journal"])
        self.assertIn("miles", data["workout"])
        self.assertIn("misses", data["work"])
        self.assertIn("repeat_missed", data["work"])


if __name__ == "__main__":
    unittest.main()
