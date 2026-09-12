"""Focus blocks: named spans, overflow, and Fill week stays off them."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import calclock
import schedule
import work


class FocusBlockTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.patcher = mock.patch.object(work, "_data_dir", lambda: self.data_dir)
        self.kinds = mock.patch.object(schedule.workouts, "expected_kinds_for_date", return_value=[])
        self.patcher.start()
        self.kinds.start()
        self.today = mock.patch.object(work, "_today", return_value=date(2026, 9, 7))
        self.today.start()
        calclock.reset_purge_cache()
        work.invalidate_work_board_cache()

    def tearDown(self) -> None:
        work.cancel_heavy_snapshot_side_effects()
        self.kinds.stop()
        self.patcher.stop()
        self.today.stop()
        self._tmp.cleanup()

    def test_overflow_is_allowed_and_visible(self) -> None:
        first = work.create_work_item("Read brief", scheduled_date="2026-09-07", estimate_minutes=45)
        second = work.create_work_item("Draft notes", scheduled_date="2026-09-07", estimate_minutes=45)
        block = calclock.create_focus_block(
            "Deep work",
            "2026-09-07T13:00:00",
            "2026-09-07T14:00:00",
            [first["id"], second["id"]],
        )
        self.assertEqual(block["kind"], "focus")
        self.assertEqual(block["minutes"], 60)
        self.assertEqual(block["planned_minutes"], 90)
        self.assertEqual(block["overflow_minutes"], 30)
        self.assertEqual(len(block["items"]), 2)
        unplaced = {row["id"] for row in calclock.unplaced_work()}
        self.assertNotIn(first["id"], unplaced)
        self.assertNotIn(second["id"], unplaced)

    def test_fill_week_does_not_pack_over_or_delete_focus(self) -> None:
        focus = calclock.create_focus_block(
            "Hold this",
            "2026-09-07T09:00:00",
            "2026-09-07T12:00:00",
            [],
        )
        work.create_work_item(
            "Study essay",
            due_at="2026-09-11T23:59:00",
            estimate_minutes=90,
        )
        with mock.patch.object(schedule, "_now", return_value=datetime(2026, 9, 7, 8, 0, 0)):
            week = schedule.fill_week("2026-09-07")
        monday = next(day for day in week["days"] if day["date"] == "2026-09-07")
        focuses = [row for row in monday["blocks"] if row.get("kind") == "focus"]
        self.assertEqual(len(focuses), 1)
        self.assertEqual(focuses[0]["id"], focus["id"])
        hold_start = datetime(2026, 9, 7, 9, 0, 0)
        hold_end = datetime(2026, 9, 7, 12, 0, 0)
        for block in monday["blocks"]:
            if block.get("kind") == "focus":
                continue
            start = calclock.parse_datetime(block["start_at"])
            end = calclock.parse_datetime(block["end_at"])
            self.assertFalse(start < hold_end and end > hold_start)

    def test_fill_week_does_not_place_attached_todos(self) -> None:
        item = work.create_work_item(
            "Inside focus",
            due_at="2026-09-11T23:59:00",
            estimate_minutes=90,
        )
        calclock.create_focus_block(
            "Morning hold",
            "2026-09-07T14:00:00",
            "2026-09-07T15:00:00",
            [item["id"]],
        )
        with mock.patch.object(schedule, "_now", return_value=datetime(2026, 9, 7, 8, 0, 0)):
            week = schedule.fill_week("2026-09-07")
        work_blocks = [row for day in week["days"] for row in day["blocks"] if row.get("kind") == "work"]
        self.assertEqual(work_blocks, [])

    def test_detach_returns_item_to_unplaced(self) -> None:
        item = work.create_work_item("Parked later", scheduled_date="2026-09-07", estimate_minutes=30)
        block = calclock.create_focus_block(
            "Hold",
            "2026-09-07T16:00:00",
            "2026-09-07T17:00:00",
            [item["id"]],
        )
        calclock.detach_focus_item(block["id"], item["id"])
        unplaced = {row["id"] for row in calclock.unplaced_work()}
        self.assertIn(item["id"], unplaced)


if __name__ == "__main__":
    unittest.main()
