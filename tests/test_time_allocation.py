"""Calendar time allocation for Analytics: last week or this month."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import calclock
import insights
import work


class TimeAllocationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name)
        self.patcher = mock.patch.object(work, "_data_dir", lambda: self.data_dir)
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()
        self.tmp.cleanup()

    def test_last_week_range_is_previous_iso_week(self) -> None:
        key, start, end = insights.allocation_range("week", date(2026, 9, 1))
        self.assertEqual(key, "week")
        self.assertEqual(start.isoformat(), "2026-08-24")
        self.assertEqual(end.isoformat(), "2026-08-30")
        key, start, end = insights.allocation_range("month", date(2026, 9, 1))
        self.assertEqual(key, "month")
        self.assertEqual(start.isoformat(), "2026-09-01")
        self.assertEqual(end.isoformat(), "2026-09-30")

    def test_minutes_by_busy_work_and_gym(self) -> None:
        _, start, _ = insights.allocation_range("week")
        calclock.create_calendar_event(
            "CHEM lecture",
            f"{start.isoformat()}T09:00:00",
            f"{start.isoformat()}T10:00:00",
        )
        calclock.add_block(
            title="Spanish",
            start=datetime(start.year, start.month, start.day, 14, 0, 0),
            end=datetime(start.year, start.month, start.day, 16, 0, 0),
            kind="work",
        )
        calclock.add_block(
            title="Legs",
            start=datetime(start.year, start.month, start.day, 17, 0, 0),
            end=datetime(start.year, start.month, start.day, 18, 0, 0),
            kind="workout",
        )
        calclock.add_block(
            title="Skipped",
            start=datetime(start.year, start.month, start.day, 19, 0, 0),
            end=datetime(start.year, start.month, start.day, 20, 0, 0),
            kind="work",
            status="skipped",
        )
        data = insights.get_time_allocation("week")
        by_id = {row["id"]: row for row in data["categories"]}
        self.assertEqual(data["period"], "week")
        self.assertEqual(by_id["hard"]["minutes"], 60)
        self.assertEqual(by_id["work"]["minutes"], 120)
        self.assertEqual(by_id["workout"]["minutes"], 60)
        self.assertEqual(data["total_minutes"], 240)
        self.assertEqual(by_id["work"]["pct"], 50)


if __name__ == "__main__":
    unittest.main()
